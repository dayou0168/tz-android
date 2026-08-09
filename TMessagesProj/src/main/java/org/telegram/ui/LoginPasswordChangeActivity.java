package org.telegram.ui;

import android.content.Context;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.EditText;
import android.widget.LinearLayout;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.R;
import org.telegram.tgnet.TLRPC;
import org.telegram.tgnet.tl.TL_account;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.AlertDialog;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Components.LayoutHelper;

import java.nio.charset.StandardCharsets;

public class LoginPasswordChangeActivity extends BaseFragment {
    private static final String PROTOCOL_HINT = "TZ_LOGIN_PASSWORD_V1";

    private EditText currentPasswordField;
    private EditText newPasswordField;
    private EditText confirmPasswordField;

    @Override
    public View createView(Context context) {
        actionBar.setBackButtonImage(R.drawable.ic_ab_back);
        actionBar.setTitle(LocaleController.getString(R.string.TZChangeLoginPassword));
        actionBar.setAllowOverlayTitle(false);
        actionBar.createMenu().addItemWithWidth(1, R.drawable.ic_ab_done, AndroidUtilities.dp(56), LocaleController.getString(R.string.Done));
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) {
                    finishFragment();
                } else if (id == 1) {
                    submit();
                }
            }
        });

        LinearLayout layout = new LinearLayout(context);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setGravity(Gravity.TOP);
        layout.setPadding(AndroidUtilities.dp(24), AndroidUtilities.dp(24), AndroidUtilities.dp(24), 0);
        layout.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundWhite));

        currentPasswordField = passwordField(context, R.string.PleaseEnterCurrentPassword);
        newPasswordField = passwordField(context, R.string.PleaseEnterNewFirstPasswordHint);
        confirmPasswordField = passwordField(context, R.string.PleaseEnterNewSecondPasswordHint);
        layout.addView(currentPasswordField, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, 52, 0, 0, 0, 0, 12));
        layout.addView(newPasswordField, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, 52, 0, 0, 0, 0, 12));
        layout.addView(confirmPasswordField, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, 52));
        fragmentView = layout;
        return fragmentView;
    }

    private EditText passwordField(Context context, int hintRes) {
        EditText field = new EditText(context);
        field.setSingleLine(true);
        field.setTextSize(17);
        field.setHint(LocaleController.getString(hintRes));
        field.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        field.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText));
        field.setHintTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteHintText));
        return field;
    }

    private void submit() {
        String current = currentPasswordField.getText().toString();
        String next = newPasswordField.getText().toString();
        String confirm = confirmPasswordField.getText().toString();
        if (current.isEmpty() || next.length() < 8) {
            showError(LocaleController.getString(R.string.TZLoginPasswordMinLength));
            return;
        }
        if (!next.equals(confirm)) {
            showError(LocaleController.getString(R.string.PasswordDoNotMatch));
            return;
        }

        TL_account.updatePasswordSettings request = new TL_account.updatePasswordSettings();
        request.password = new TLRPC.TL_inputCheckPasswordEmpty();
        request.new_settings = new TL_account.passwordInputSettings();
        request.new_settings.flags = 1;
        request.new_settings.new_algo = new TLRPC.TL_passwordKdfAlgoUnknown();
        request.new_settings.new_password_hash = (current + "\0" + next).getBytes(StandardCharsets.UTF_8);
        request.new_settings.hint = PROTOCOL_HINT;

        AlertDialog progress = new AlertDialog(getParentActivity(), AlertDialog.ALERT_TYPE_SPINNER);
        progress.setCanCancel(false);
        progress.show();
        getConnectionsManager().sendRequest(request, (response, error) -> AndroidUtilities.runOnUIThread(() -> {
            progress.dismiss();
            if (error == null) {
                new AlertDialog.Builder(getParentActivity())
                        .setTitle(LocaleController.getString(R.string.YourPasswordSuccess))
                        .setMessage(LocaleController.getString(R.string.TZLoginPasswordChanged))
                        .setPositiveButton(LocaleController.getString(R.string.OK), (dialog, which) -> finishFragment())
                        .show();
            } else if (error.text != null && error.text.contains("PASSWORD_HASH_INVALID")) {
                showError(LocaleController.getString(R.string.CheckPasswordWrong));
            } else {
                showError(error.text == null ? LocaleController.getString(R.string.ErrorOccurred) : error.text);
            }
        }));
    }

    private void showError(String message) {
        if (getParentActivity() == null) {
            return;
        }
        new AlertDialog.Builder(getParentActivity())
                .setTitle(LocaleController.getString(R.string.AppName))
                .setMessage(message)
                .setPositiveButton(LocaleController.getString(R.string.OK), null)
                .show();
    }
}
