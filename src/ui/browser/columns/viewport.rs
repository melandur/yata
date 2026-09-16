// SPDX-License-Identifier: MIT

//! Fixed-slot column viewport.
//!
//! Miller columns normally grow one pane per folder and scroll horizontally.
//! With the Yazi-style preference the browser instead keeps a fixed number of
//! slots on screen and shifts their contents, so descending never widens the
//! strip and never scrolls it.

use super::{COLUMN_WIDTH, ColumnView};
use crate::ui::browser::ViewState;
use gtk::prelude::*;
use std::rc::Rc;

/// Slots kept on screen: parent, current, and the current row's child.
pub(in crate::ui) const VIEWPORT_SLOTS: usize = 3;

/// Yazi's `mgr.ratio`, over parent / current / child.
const SLOT_RATIOS: [u32; VIEWPORT_SLOTS] = [1, 4, 3];

/// Below this the strip gives up and scrolls instead. The parent slot only gets
/// an eighth, so a floor near a column width would veto the ratio outright.
pub(in crate::ui) const MIN_SLOT_WIDTH: i32 = 72;

/// Splits `viewport` across `ratios`, handing the rounding remainder to the
/// widest slot so the strip covers the viewport exactly.
fn slot_widths(viewport: i32, ratios: &[u32]) -> Option<Vec<i32>> {
    let total: u32 = ratios.iter().sum();
    if total == 0 || viewport <= 0 {
        return None;
    }
    let mut widths: Vec<i32> = ratios
        .iter()
        .map(|ratio| (i64::from(viewport) * i64::from(*ratio) / i64::from(total)) as i32)
        .collect();
    if widths.iter().any(|width| *width < MIN_SLOT_WIDTH) {
        return None;
    }
    let assigned: i32 = widths.iter().sum();
    let widest = ratios
        .iter()
        .enumerate()
        .max_by_key(|(_, ratio)| **ratio)
        .map(|(index, _)| index)?;
    widths[widest] += viewport - assigned;
    Some(widths)
}

fn restore_column(column: &ColumnView) {
    column.shell.set_visible(true);
    column.resize_handle.set_visible(true);
    column
        .shell
        .set_size_request(column.manual_width.get().max(COLUMN_WIDTH), -1);
}

impl ViewState {
    /// Width the fixed slots cannot give up, so the preview pane can still open
    /// against a strip that already fills the viewport.
    pub(in crate::ui) fn minimum_viewport_width(&self) -> i32 {
        let visible = self.columns.borrow().len().min(VIEWPORT_SLOTS) as i32;
        visible * MIN_SLOT_WIDTH
    }

    pub(in crate::ui) fn viewport_width(&self) -> i32 {
        let page = self.scroller.hadjustment().page_size().round() as i32;
        let page = if page > 0 {
            page
        } else {
            self.scroller.width()
        };
        page - self.columns_widget.margin_end()
    }

    /// Applies the fixed-slot layout, or restores free-growing columns when the
    /// preference is off or the viewport is too narrow to divide.
    pub(in crate::ui) fn sync_column_viewport(self: &Rc<Self>) {
        let columns = self.columns.borrow();
        let widths = self
            .yazi_columns
            .get()
            .then(|| {
                // Anchored on the focused column, not the deepest: a child
                // column appears and disappears as the cursor crosses folders,
                // which otherwise slides the current folder between slots.
                let active = self
                    .browser
                    .active_depth()
                    .unwrap_or_else(|| columns.len().saturating_sub(1));
                let first = active.saturating_sub(1);
                slot_widths(self.viewport_width(), &SLOT_RATIOS).map(|widths| (first, widths))
            })
            .flatten();

        let Some((first, widths)) = widths else {
            self.columns_widget.set_halign(gtk::Align::Start);
            self.scroller
                .set_hscrollbar_policy(gtk::PolicyType::Automatic);
            for column in columns.iter() {
                restore_column(column);
            }
            return;
        };

        self.columns_widget.set_halign(gtk::Align::Fill);
        self.scroller
            .set_hscrollbar_policy(gtk::PolicyType::External);
        for (index, column) in columns.iter().enumerate() {
            let Some(width) = index.checked_sub(first).and_then(|slot| widths.get(slot)) else {
                column.shell.set_visible(false);
                continue;
            };
            column.shell.set_visible(true);
            column.resize_handle.set_visible(false);
            // The width is only a request; expanding columns would split the
            // strip's spare space evenly and hide the ratio.
            column.shell.set_hexpand(false);
            column.shell.set_size_request(*width, -1);
        }
    }

    /// Re-divides the slots whenever the viewport itself changes width.
    pub(in crate::ui) fn track_column_viewport(self: &Rc<Self>) {
        let weak = Rc::downgrade(self);
        self.scroller
            .hadjustment()
            .connect_page_size_notify(move |_| {
                if let Some(state) = weak.upgrade() {
                    state.sync_column_viewport();
                }
            });
    }

    pub(in crate::ui) fn set_yazi_columns(self: &Rc<Self>, enabled: bool) {
        if self.yazi_columns.replace(enabled) == enabled {
            return;
        }
        self.cancel_child_preview();
        self.browser.set_shifting_columns(enabled);
        self.sync_column_viewport();
        let deepest = self
            .columns
            .borrow()
            .last()
            .map(|column| column.shell.clone());
        if !enabled && let Some(deepest) = deepest {
            self.reveal_column(deepest);
        }
    }
}

#[cfg(test)]
mod tests;
