#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#import <objc/message.h>
#import <mach-o/dyld.h>

#ifndef AF_PRESERVE_CLOUDKIT
#define AF_PRESERVE_CLOUDKIT 0
#endif

static id localUser;
static NSDictionary *identity;
static BOOL installed;
static id offlineContainer;
static id offlineDatabase;

static void installLocalFeatureFlags(void) {
    NSUserDefaults *defaults = NSUserDefaults.standardUserDefaults;
    NSMutableDictionary *arguments = [[defaults volatileDomainForName:NSArgumentDomain] mutableCopy];
    if (!arguments) arguments = [NSMutableDictionary dictionary];
    NSString *key = @"transientFeatureFlagOverrides";
    NSString *existing = arguments[key] ?: [defaults stringForKey:key];
    NSMutableArray *pairs = [NSMutableArray array];
    for (NSString *pair in [existing componentsSeparatedByString:@"|"]) {
        NSString *name = [pair componentsSeparatedByString:@"="].firstObject;
        if (pair.length && ![name isEqualToString:@"arc-force-sign-out-enabled"] &&
            ![name isEqualToString:@"arc-updates-dialog-enabled"]) [pairs addObject:pair];
    }
    [pairs addObjectsFromArray:@[@"arc-force-sign-out-enabled=false", @"arc-updates-dialog-enabled=false"]];
    arguments[key] = [pairs componentsJoinedByString:@"|"];
    [defaults setVolatileDomain:arguments forName:NSArgumentDomain];
}

static void record(NSString *event) {
    const char *path = getenv("ARC_FOREVER_LOG");
    if (!path) return;
    FILE *file = fopen(path, "a");
    if (file) { fprintf(file, "%s\n", event.UTF8String); fclose(file); }
}

static NSDictionary *loadIdentity(void) {
    NSString *path = NSProcessInfo.processInfo.environment[@"ARC_FOREVER_STATE_PATH"];
    if (!path) path = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/Arc/StorableAuthState.json"];
    NSData *data = [NSData dataWithContentsOfFile:path];
    NSDictionary *state = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:NULL] : nil;
    id session = [state isKindOfClass:NSDictionary.class] ? state[@"session"] : nil;
    NSDictionary *user = [session isKindOfClass:NSDictionary.class] ? session[@"user"] : nil;
    if (![user isKindOfClass:NSDictionary.class]) {
        NSString *receiptPath = [NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:@"ArcForever.json"];
        NSData *receiptData = [NSData dataWithContentsOfFile:receiptPath];
        NSDictionary *receipt = receiptData ? [NSJSONSerialization JSONObjectWithData:receiptData options:0 error:NULL] : nil;
        NSString *backupPath = [receipt isKindOfClass:NSDictionary.class] ? receipt[@"auth_backup"] : nil;
        NSData *backup = [backupPath isKindOfClass:NSString.class] ? [NSData dataWithContentsOfFile:backupPath] : nil;
        NSDictionary *saved = backup ? [NSJSONSerialization JSONObjectWithData:backup options:0 error:NULL] : nil;
        id savedSession = [saved isKindOfClass:NSDictionary.class] ? saved[@"session"] : nil;
        id savedUser = [savedSession isKindOfClass:NSDictionary.class] ? savedSession[@"user"] : nil;
        if ([savedUser isKindOfClass:NSDictionary.class] && [savedUser[@"id"] isKindOfClass:NSString.class]) {
            [backup writeToFile:path atomically:YES];
            user = savedUser;
            record(@"identity:restored-local-cache");
        }
    }
    if (![user isKindOfClass:NSDictionary.class] || ![user[@"id"] isKindOfClass:NSString.class]) {
        record(@"identity:missing-local-state");
        return @{@"id": @"arc-forever-local", @"email": @"local@arc-forever.invalid", @"name": @"Local User", @"avatarUrl": @"file:///dev/null", @"createdAt": @0};
    }
    record(@"identity:loaded-local-state");
    return user;
}

@interface AFUserMetadata : NSObject
@property(nonatomic, readonly) NSDate *creationDate;
@property(nonatomic, readonly) NSDate *lastSignInDate;
@end
@implementation AFUserMetadata
- (NSDate *)creationDate { return [NSDate dateWithTimeIntervalSinceReferenceDate:[identity[@"createdAt"] doubleValue]]; }
- (NSDate *)lastSignInDate { return self.creationDate; }
@end

@interface AFListenerRegistration : NSObject
- (void)remove;
@end
@implementation AFListenerRegistration
- (void)remove { }
@end

static id userID(id self, SEL cmd) { return identity[@"id"]; }
static id userName(id self, SEL cmd) { return identity[@"name"] ?: @"Local User"; }
static id userEmail(id self, SEL cmd) { return identity[@"email"] ?: @"local@arc-forever.invalid"; }
static id userPhoto(id self, SEL cmd) { return nil; }
static id userProvider(id self, SEL cmd) { return @"firebase"; }
static id emptyArray(id self, SEL cmd) { return @[]; }
static id noObject(id self, SEL cmd) { return nil; }
static BOOL yesValue(id self, SEL cmd) { return YES; }
static BOOL noValue(id self, SEL cmd) { return NO; }
static id userMetadata(id self, SEL cmd) { return [AFUserMetadata new]; }

static NSError *offlineError(void) {
    return [NSError errorWithDomain:NSURLErrorDomain code:NSURLErrorNotConnectedToInternet
                           userInfo:@{NSLocalizedDescriptionKey: @"Arc Forever uses a local identity. Cloud authentication is disabled."}];
}

static void reload(id self, SEL cmd, void (^completion)(NSError *)) {
    record(@"user:reload-local-success");
    if (completion) dispatch_async(dispatch_get_main_queue(), ^{ completion(nil); });
}

static void token(id self, SEL cmd, BOOL force, void (^completion)(id, NSError *)) {
    record(@"auth:cloud-token-disabled");
    if (completion) dispatch_async(dispatch_get_main_queue(), ^{ completion(nil, offlineError()); });
}

static void tokenSimple(id self, SEL cmd, void (^completion)(id, NSError *)) { token(self, cmd, NO, completion); }
static void ignoreError(id self, SEL cmd, NSError *error) { record(@"auth:remote-signout-ignored"); }
static void noAction(id self, SEL cmd) { }
static void noDelay(id self, SEL cmd, double delay, BOOL retry) { }
static void noActionWithSender(id self, SEL cmd, id sender) { }
static void ignoreSetting(id self, SEL cmd, BOOL enabled) { }

static id documentListener(id self, SEL cmd, void (^listener)(id, NSError *)) {
    record(@"firestore:local-fallback-requested");
    if (listener) dispatch_async(dispatch_get_main_queue(), ^{ listener(nil, offlineError()); });
    return [AFListenerRegistration new];
}
static id documentListenerMetadata(id self, SEL cmd, BOOL metadata, void (^listener)(id, NSError *)) {
    return documentListener(self, cmd, listener);
}
static id documentListenerOptions(id self, SEL cmd, id options, void (^listener)(id, NSError *)) {
    return documentListener(self, cmd, listener);
}

static id cloudContainer(id self, SEL cmd) { return offlineContainer; }
static id cloudContainerNamed(id self, SEL cmd, id name) { return offlineContainer; }
static id cloudDatabase(id self, SEL cmd) { return offlineDatabase; }
static id cloudIdentifier(id self, SEL cmd) { return @"iCloud.company.thebrowser.Browser"; }
static NSInteger cloudScope(id self, SEL cmd) { return 2; }
static void cloudAccountStatus(id self, SEL cmd, void (^completion)(NSInteger, NSError *)) {
    record(@"cloudkit:no-cloud-account");
    if (completion) dispatch_async(dispatch_get_main_queue(), ^{ completion(3, nil); });
}
static void cloudFetchUser(id self, SEL cmd, void (^completion)(id, NSError *)) {
    if (completion) dispatch_async(dispatch_get_main_queue(), ^{ completion(nil, offlineError()); });
}
static void cloudAddOperation(id self, SEL cmd, id operation) {
    record(@"cloudkit:operation-disabled");
    dispatch_async(dispatch_get_main_queue(), ^{
        for (NSString *name in @[@"fetchRecordsCompletionBlock", @"fetchRecordZonesCompletionBlock", @"fetchSubscriptionsCompletionBlock"]) {
            SEL getter = NSSelectorFromString(name);
            if ([operation respondsToSelector:getter]) {
                void (^completion)(id, NSError *) = ((id (*)(id, SEL))objc_msgSend)(operation, getter);
                if (completion) completion(nil, offlineError());
            }
        }
        for (NSString *name in @[@"modifyRecordsCompletionBlock", @"modifyRecordZonesCompletionBlock", @"modifySubscriptionsCompletionBlock"]) {
            SEL getter = NSSelectorFromString(name);
            if ([operation respondsToSelector:getter]) {
                void (^completion)(id, id, NSError *) = ((id (*)(id, SEL))objc_msgSend)(operation, getter);
                if (completion) completion(nil, nil, offlineError());
            }
        }
        SEL changes = sel_registerName("fetchRecordZoneChangesCompletionBlock");
        if ([operation respondsToSelector:changes]) {
            void (^completion)(NSError *) = ((id (*)(id, SEL))objc_msgSend)(operation, changes);
            if (completion) completion(offlineError());
        }
    });
}

static id currentUser(id self, SEL cmd) {
    record(@"auth:current-local-user");
    return localUser;
}

static id addListener(id self, SEL cmd, void (^listener)(id, id)) {
    record(@"auth:local-listener-added");
    id handle = [NSObject new];
    if (listener) dispatch_async(dispatch_get_main_queue(), ^{ listener(self, localUser); });
    return handle;
}

static void removeListener(id self, SEL cmd, id handle) { }
static BOOL signOut(id self, SEL cmd, NSError **error) {
    if (error) *error = nil;
    record(@"auth:signout-kept-local");
    return YES;
}
static BOOL forcedSignOut(id self, SEL cmd, id uid, NSError **error) { return signOut(self, cmd, error); }
static BOOL saveUser(id self, SEL cmd, id user, NSError **error) { if (error) *error = nil; return YES; }
static BOOL getUser(id self, SEL cmd, id __autoreleasing *user, NSError **error) {
    if (user) *user = localUser;
    if (error) *error = nil;
    record(@"auth:keychain-replaced-by-local-state");
    return YES;
}
static id storedUser(id self, SEL cmd, id group, NSError **error) { if (error) *error = nil; return localUser; }
static BOOL updateUser(id self, SEL cmd, id user, BOOL force, BOOL save, NSError **error) {
    if (error) *error = nil;
    record(@"auth:remote-user-change-ignored");
    return YES;
}

static void override(Class cls, const char *selector, IMP imp, const char *fallbackType) {
    SEL sel = sel_registerName(selector);
    Method method = class_getInstanceMethod(cls, sel);
    const char *types = method ? method_getTypeEncoding(method) : fallbackType;
    if (!class_addMethod(cls, sel, imp, types)) class_replaceMethod(cls, sel, imp, types);
}

static void install(void) {
    if (installed) return;
    Class auth = objc_getClass("FIRAuth");
    Class user = objc_getClass("FIRUser");
    if (!auth || !user) return;
    identity = loadIdentity();
    Class local = objc_allocateClassPair(user, "ArcForeverLocalFIRUser", 0);
    if (!local) { record(@"guard:error-local-class-unavailable"); return; }
    override(local, "uid", (IMP)userID, "@@:");
    override(local, "displayName", (IMP)userName, "@@:");
    override(local, "email", (IMP)userEmail, "@@:");
    override(local, "photoURL", (IMP)userPhoto, "@@:");
    override(local, "providerID", (IMP)userProvider, "@@:");
    override(local, "providerData", (IMP)emptyArray, "@@:");
    override(local, "metadata", (IMP)userMetadata, "@@:");
    override(local, "isAnonymous", (IMP)noValue, "B@:");
    override(local, "isEmailVerified", (IMP)yesValue, "B@:");
    override(local, "refreshToken", (IMP)noObject, "@@:");
    override(local, "rawAccessToken", (IMP)noObject, "@@:");
    override(local, "reloadWithCompletion:", (IMP)reload, "v@:@?");
    override(local, "getIDTokenWithCompletion:", (IMP)tokenSimple, "v@:@?");
    override(local, "getIDTokenForcingRefresh:completion:", (IMP)token, "v@:B@?");
    override(local, "getIDTokenResultWithCompletion:", (IMP)tokenSimple, "v@:@?");
    override(local, "getIDTokenResultForcingRefresh:completion:", (IMP)token, "v@:B@?");
    override(local, "internalGetTokenWithCallback:", (IMP)tokenSimple, "v@:@?");
    override(local, "internalGetTokenForcingRefresh:callback:", (IMP)token, "v@:B@?");
    override(local, "signOutIfTokenIsInvalidWithError:", (IMP)ignoreError, "v@:@");
    objc_registerClassPair(local);
    localUser = class_createInstance(local, 0);

    override(auth, "currentUser", (IMP)currentUser, "@@:");
    override(auth, "getUserID", (IMP)userID, "@@:");
    override(auth, "getUser:error:", (IMP)getUser, "B@:^@^@");
    override(auth, "getStoredUserForAccessGroup:error:", (IMP)storedUser, "@@:@^@");
    override(auth, "saveUser:error:", (IMP)saveUser, "B@:@^@");
    override(auth, "updateKeychainWithUser:error:", (IMP)saveUser, "B@:@^@");
    override(auth, "updateCurrentUser:byForce:savingToDisk:error:", (IMP)updateUser, "B@:@BB^@");
    override(auth, "addAuthStateDidChangeListener:", (IMP)addListener, "@@:@?");
    override(auth, "removeAuthStateDidChangeListener:", (IMP)removeListener, "v@:@");
    override(auth, "addIDTokenDidChangeListener:", (IMP)addListener, "@@:@?");
    override(auth, "removeIDTokenDidChangeListener:", (IMP)removeListener, "v@:@");
    override(auth, "signOut:", (IMP)signOut, "B@:^@");
    override(auth, "signOutByForceWithUserID:error:", (IMP)forcedSignOut, "B@:@^@");
    override(auth, "getTokenForcingRefresh:withCallback:", (IMP)token, "v@:B@?");
    override(auth, "scheduleAutoTokenRefresh", (IMP)noAction, "v@:");
    override(auth, "scheduleAutoTokenRefreshWithDelay:retry:", (IMP)noDelay, "v@:dB");

    Class document = objc_getClass("FIRDocumentReference");
    if (document) {
        override(document, "addSnapshotListener:", (IMP)documentListener, "@@:@?");
        override(document, "addSnapshotListenerWithIncludeMetadataChanges:listener:", (IMP)documentListenerMetadata, "@@:B@?");
        override(document, "addSnapshotListenerWithOptions:listener:", (IMP)documentListenerOptions, "@@:@@?");
    }

#if !AF_PRESERVE_CLOUDKIT
    Class container = objc_getClass("CKContainer");
    Class database = objc_getClass("CKDatabase");
    if (container && database) {
        Class localContainer = objc_allocateClassPair(container, "ArcForeverOfflineCKContainer", 0);
        Class localDatabase = objc_allocateClassPair(database, "ArcForeverOfflineCKDatabase", 0);
        override(localContainer, "containerIdentifier", (IMP)cloudIdentifier, "@@:");
        override(localContainer, "privateCloudDatabase", (IMP)cloudDatabase, "@@:");
        override(localContainer, "publicCloudDatabase", (IMP)cloudDatabase, "@@:");
        override(localContainer, "sharedCloudDatabase", (IMP)cloudDatabase, "@@:");
        override(localContainer, "accountStatusWithCompletionHandler:", (IMP)cloudAccountStatus, "v@:@?");
        override(localContainer, "fetchUserRecordIDWithCompletionHandler:", (IMP)cloudFetchUser, "v@:@?");
        override(localContainer, "addOperation:", (IMP)cloudAddOperation, "v@:@");
        override(localDatabase, "databaseScope", (IMP)cloudScope, "q@:");
        override(localDatabase, "addOperation:", (IMP)cloudAddOperation, "v@:@");
        objc_registerClassPair(localContainer);
        objc_registerClassPair(localDatabase);
        offlineContainer = class_createInstance(localContainer, 0);
        offlineDatabase = class_createInstance(localDatabase, 0);
        override(object_getClass(container), "defaultContainer", (IMP)cloudContainer, "@@:");
        override(object_getClass(container), "containerWithIdentifier:", (IMP)cloudContainerNamed, "@@:@");
        record(@"cloudkit:local-container-installed");
    }
#endif

    for (const char **name = (const char *[]){"SUUpdater", "SPUUpdater", NULL}; *name; name++) {
        Class updater = objc_getClass(*name);
        if (updater) {
            override(updater, "automaticallyChecksForUpdates", (IMP)noValue, "B@:");
            override(updater, "automaticallyDownloadsUpdates", (IMP)noValue, "B@:");
            override(updater, "setAutomaticallyChecksForUpdates:", (IMP)ignoreSetting, "v@:B");
            override(updater, "setAutomaticallyDownloadsUpdates:", (IMP)ignoreSetting, "v@:B");
            override(updater, "checkForUpdatesInBackground", (IMP)noAction, "v@:");
            override(updater, "checkForUpdates:", (IMP)noActionWithSender, "v@:@");
        }
    }
    [NSUserDefaults.standardUserDefaults registerDefaults:@{@"SUEnableAutomaticChecks": @NO,
        @"SUAutomaticallyUpdate": @NO, @"SUAllowsAutomaticUpdates": @NO}];
    installed = YES;
    record(@"guard:installed-local-auth");
}

__attribute__((constructor)) static void start(void) {
    @autoreleasepool { installLocalFeatureFlags(); install(); }
}

__attribute__((visibility("default"))) int ArcForeverGuardInstalled(void) { return installed && localUser != nil; }
