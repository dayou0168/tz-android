/*
 * This is the source code of Telegram for Android v. 5.x.x.
 * It is licensed under GNU GPL v. 2 or later.
 * You should have received a copy of the license in this archive (see LICENSE).
 *
 * Copyright Nikolai Kudashov, 2013-2018.
 */

package org.telegram.messenger;

import androidx.annotation.NonNull;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

import org.telegram.tgnet.ConnectionsManager;

import java.util.Map;

public class GcmPushListenerService extends FirebaseMessagingService {

    @Override
    public void onMessageReceived(RemoteMessage message) {
        String from = message.getFrom();
        Map<String, String> data = message.getData();
        long time = message.getSentTime();

        if (BuildVars.LOGS_ENABLED) {
            FileLog.d("FCM received data: " + data + " from: " + from);
        }

        // TZ's server intentionally sends only an authenticated, content-free
        // wake-up marker through FCM. The actual update remains on MTProto, so
        // message text and media never pass through Firebase.
        if ("1".equals(data.get("tz_sync"))) {
            ApplicationLoader.postInitApplication();
            final long targetUserId = Utilities.parseLong(data.get("user_id"));
            AndroidUtilities.runOnUIThread(() -> {
                for (int account = 0; account < UserConfig.MAX_ACCOUNT_COUNT; account++) {
                    UserConfig userConfig = UserConfig.getInstance(account);
                    if (!userConfig.isClientActivated()) {
                        continue;
                    }
                    if (targetUserId != 0 && userConfig.getClientUserId() != targetUserId) {
                        continue;
                    }
                    ConnectionsManager.getInstance(account).resumeNetworkMaybe();
                }
            });
            return;
        }

        String encryptedPayload = data.get("p");
        if (encryptedPayload != null) {
            PushListenerController.processRemoteMessage(PushListenerController.PUSH_TYPE_FIREBASE, encryptedPayload, time);
        }
    }

    @Override
    public void onNewToken(@NonNull String token) {
        AndroidUtilities.runOnUIThread(() -> {
            if (BuildVars.LOGS_ENABLED) {
                FileLog.d("Refreshed FCM token: " + token);
            }
            ApplicationLoader.postInitApplication();
            PushListenerController.sendRegistrationToServer(PushListenerController.PUSH_TYPE_FIREBASE, token);
        });
    }
}
