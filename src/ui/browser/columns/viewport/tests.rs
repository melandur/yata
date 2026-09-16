// SPDX-License-Identifier: MIT

use super::*;

#[test]
fn the_current_slot_is_the_widest() {
    let widest = SLOT_RATIOS
        .iter()
        .enumerate()
        .max_by_key(|(_, ratio)| **ratio)
        .map(|(index, _)| index);
    assert_eq!(
        widest,
        Some(1),
        "the current folder sits in the middle slot"
    );
}

#[test]
fn the_ratios_match_yazi() {
    assert_eq!(SLOT_RATIOS, [1, 4, 3]);
}

#[test]
fn slots_cover_the_viewport_exactly() {
    for viewport in [1600, 1601, 1602, 1603, 1920] {
        let widths = slot_widths(viewport, &SLOT_RATIOS).expect("divisible viewport");
        assert_eq!(widths.iter().sum::<i32>(), viewport);
    }
}

/// The strip is anchored on the focused column, so hovering a file instead of a
/// folder must not resize anything: the slot widths depend only on the viewport.
#[test]
fn slot_widths_depend_only_on_the_viewport() {
    let hovering_folder = slot_widths(1440, &SLOT_RATIOS).expect("divisible viewport");
    let hovering_file = slot_widths(1440, &SLOT_RATIOS).expect("divisible viewport");
    assert_eq!(hovering_folder, hovering_file);
    assert_eq!(hovering_folder, vec![180, 720, 540]);
}

/// A window wide enough to give the parent slot its eighth keeps the ratio. The
/// old floor of a full column width vetoed the strip on ordinary windows, which
/// dropped every column back to free-growing widths.
#[test]
fn ordinary_windows_keep_the_ratio() {
    for viewport in [900, 1280, 1440, 1920, 2560] {
        assert!(
            slot_widths(viewport, &SLOT_RATIOS).is_some(),
            "viewport {viewport} should divide"
        );
    }
}

#[test]
fn viewports_too_narrow_to_divide_keep_free_growing_columns() {
    // The parent slot takes an eighth, so it drops under MIN_SLOT_WIDTH here.
    assert!(slot_widths(MIN_SLOT_WIDTH * 8 - 8, &SLOT_RATIOS).is_none());
    assert!(slot_widths(0, &SLOT_RATIOS).is_none());
}

/// Opening the drawer swaps it in for the child column, so the parent and the
/// current folder must keep the widths they had with the strip at full width.
#[test]
fn opening_the_drawer_does_not_move_the_other_panes() {
    let window = 1800;
    let closed = slot_widths(window, &SLOT_RATIOS).expect("full strip");
    let strip = window * 5 / 8;
    let open = slot_widths(strip, &SLOT_RATIOS_WITH_PREVIEW).expect("strip beside the drawer");
    assert_eq!(&closed[..2], &open[..]);
    assert_eq!(closed[2], window - strip, "the drawer takes the child slot");
}
