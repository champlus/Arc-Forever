#import <Foundation/Foundation.h>
#import <dlfcn.h>
static int originalCalls;
@interface FIRUser : NSObject
- (NSString *)uid;
- (void)reloadWithCompletion:(void (^)(NSError *))callback;
- (void)getIDTokenForcingRefresh:(BOOL)force completion:(void (^)(id, NSError *))callback;
@end
@implementation FIRUser
- (NSString *)uid { originalCalls++; return nil; }
- (void)reloadWithCompletion:(void (^)(NSError *))callback { originalCalls++; }
- (void)getIDTokenForcingRefresh:(BOOL)force completion:(void (^)(id, NSError *))callback { originalCalls++; }
@end
@interface FIRAuth : NSObject
- (FIRUser *)currentUser;
- (id)addAuthStateDidChangeListener:(void (^)(id, id))callback;
- (BOOL)signOutByForceWithUserID:(id)uid error:(NSError **)error;
@end
@implementation FIRAuth
- (FIRUser *)currentUser { originalCalls++; return nil; }
- (id)addAuthStateDidChangeListener:(void (^)(id, id))callback { originalCalls++; return nil; }
- (BOOL)signOutByForceWithUserID:(id)uid error:(NSError **)error { originalCalls++; return NO; }
@end
@interface FIRDocumentReference : NSObject
- (id)addSnapshotListener:(void (^)(id, NSError *))listener;
@end
@implementation FIRDocumentReference
- (id)addSnapshotListener:(void (^)(id, NSError *))listener { originalCalls++; return nil; }
@end

int main(int argc, const char **argv) {
    @autoreleasepool {
        [NSUserDefaults.standardUserDefaults setVolatileDomain:@{
            @"transientFeatureFlagOverrides": @"unrelated=true|arc-force-sign-out-enabled=true",
            @"unrelatedArgument": @"preserve"
        } forName:NSArgumentDomain];
        void *library = dlopen(argv[1], RTLD_NOW);
        if (!library) { fprintf(stderr, "%s\n", dlerror()); return 1; }
        int (*installed)(void) = dlsym(library, "ArcForeverGuardInstalled");
        NSCAssert(installed && installed(), @"Guard must install against runtime Firebase classes");
        NSString *flags = [NSUserDefaults.standardUserDefaults stringForKey:@"transientFeatureFlagOverrides"];
        NSCAssert([flags containsString:@"arc-force-sign-out-enabled=false"] &&
                  [flags containsString:@"arc-updates-dialog-enabled=false"] &&
                  ![flags containsString:@"arc-force-sign-out-enabled=true"] &&
                  [flags containsString:@"unrelated=true"], @"Local flags must defeat shutdown without discarding other overrides");
        NSCAssert([[NSUserDefaults.standardUserDefaults stringForKey:@"unrelatedArgument"] isEqualToString:@"preserve"], @"Unrelated arguments must survive");
        FIRAuth *auth = [FIRAuth new];
        FIRUser *user = auth.currentUser;
        NSCAssert([user isKindOfClass:FIRUser.class], @"Local user must satisfy Firebase class checks");
        NSCAssert([user.uid isEqualToString:@"test-local-id"], @"Identity must come from supplied local state");
        __block int callbacks = 0;
        [auth addAuthStateDidChangeListener:^(id sender, id received) {
            NSCAssert(sender == auth && received == user, @"Listeners must receive local identity"); callbacks++;
        }];
        [user reloadWithCompletion:^(NSError *error) { NSCAssert(error == nil, @"Reload must stay local"); callbacks++; }];
        [user getIDTokenForcingRefresh:YES completion:^(id token, NSError *error) {
            NSCAssert(token == nil && error.code == NSURLErrorNotConnectedToInternet, @"Never mint a cloud credential"); callbacks++;
        }];
        FIRDocumentReference *document = [FIRDocumentReference new];
        id listener = [document addSnapshotListener:^(id snapshot, NSError *error) {
            NSCAssert(snapshot == nil && error.code == NSURLErrorNotConnectedToInternet, @"Request cached app fallback"); callbacks++;
        }];
        NSCAssert([listener respondsToSelector:@selector(remove)], @"Registration must support removal");
        NSError *error = nil;
        NSCAssert([auth signOutByForceWithUserID:@"disabled-user" error:&error], @"Forced signout should complete locally");
        NSCAssert(auth.currentUser == user, @"Account revocation must not clear local identity");
        NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:3];
        while (callbacks < 4 && deadline.timeIntervalSinceNow > 0)
            [NSRunLoop.mainRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.01]];
        NSCAssert(callbacks == 4, @"All async completions must execute");
        NSCAssert(originalCalls == 0, @"No original auth/network path should execute");
        puts("{\"guard_installed\":true,\"callbacks\":4,\"original_auth_calls\":0,\"forced_signout_preserved_identity\":true}");
    }
    return 0;
}
