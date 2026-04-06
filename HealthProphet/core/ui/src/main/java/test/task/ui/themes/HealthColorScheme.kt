package test.task.ui.themes

import androidx.annotation.ColorRes
import test.task.ui.R

enum class HealthColorScheme(
    @ColorRes val bgPrimary: Int,
    @ColorRes val textPrimary: Int,
    @ColorRes val textSecondary: Int,
    @ColorRes val textError: Int,
    @ColorRes val navigationBg: Int,
    @ColorRes val navigationSelectedBg: Int,
    @ColorRes val navigationSelectedText: Int,
    @ColorRes val textFieldBgFocused: Int,
    @ColorRes val textFieldBgUnfocused: Int,
    @ColorRes val textFieldBorderFocused: Int,
    @ColorRes val textFieldBorderUnfocused: Int,
    @ColorRes val textFieldCursor: Int,
    @ColorRes val switchCheckedThumb: Int,
    @ColorRes val switchUncheckedThumb: Int,
    @ColorRes val switchCheckedTrack: Int,
    @ColorRes val switchUncheckedTrack: Int,
    @ColorRes val loadButton: Int,
    @ColorRes val progressBar: Int,
    @ColorRes val textTableHeader: Int,
    @ColorRes val borderPrimary: Int
) {
    LIGHT(
        bgPrimary = R.color.light_bg_primary,
        textPrimary = R.color.light_text_primary,
        textSecondary = R.color.light_text_secondary,
        textError = R.color.light_text_error,
        navigationBg = R.color.light_navigation_bg,
        navigationSelectedBg = R.color.light_navigation_bg_selected,
        navigationSelectedText = R.color.light_navigation_bg_selected_text,
        // --- ДОБАВЛЕННЫЕ ПОЛЯ ДЛЯ LIGHT ТЕМЫ ---
        textFieldBgFocused = R.color.light_text_field_bg_focused,
        textFieldBgUnfocused = R.color.light_text_field_bg_unfocused,
        textFieldBorderFocused = R.color.light_text_field_border_focused,
        textFieldBorderUnfocused = R.color.light_text_field_border_unfocused,
        textFieldCursor = R.color.light_text_field_cursor,
        switchCheckedThumb = R.color.light_switch_checked_thumb,
        switchUncheckedThumb = R.color.light_switch_unchecked_thumb,
        switchCheckedTrack = R.color.light_switch_checked_track,
        switchUncheckedTrack = R.color.light_switch_unchecked_track,
        loadButton = R.color.light_load_button,
        progressBar = R.color.light_progress_bar,
        textTableHeader = R.color.light_text_table_header,
        borderPrimary = R.color.light_border_primary
    ),

    DARK(
        bgPrimary = R.color.dark_bg_primary,
        textPrimary = R.color.dark_text_primary,
        textSecondary = R.color.dark_text_secondary,
        textError = R.color.dark_text_error,
        navigationBg = R.color.dark_navigation_bg,
        navigationSelectedBg = R.color.dark_navigation_bg_selected,
        navigationSelectedText = R.color.dark_navigation_bg_selected_text,
        // --- ДОБАВЛЕННЫЕ ПОЛЯ ДЛЯ DARK ТЕМЫ ---
        textFieldBgFocused = R.color.dark_text_field_bg_focused,
        textFieldBgUnfocused = R.color.dark_text_field_bg_unfocused,
        textFieldBorderFocused = R.color.dark_text_field_border_focused,
        textFieldBorderUnfocused = R.color.dark_text_field_border_unfocused,
        textFieldCursor = R.color.dark_text_field_cursor,
        switchCheckedThumb = R.color.dark_switch_checked_thumb,
        switchUncheckedThumb = R.color.dark_switch_unchecked_thumb,
        switchCheckedTrack = R.color.dark_switch_checked_track,
        switchUncheckedTrack = R.color.dark_switch_unchecked_track,
        loadButton = R.color.dark_load_button,
        progressBar = R.color.dark_progress_bar,
        textTableHeader = R.color.dark_text_table_header,
        borderPrimary = R.color.dark_border_primary
    );
}