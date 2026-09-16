// SPDX-License-Identifier: MIT

//! Yazi's file-type icons: Nerd Font glyphs coloured per file type.

use std::{collections::HashMap, sync::OnceLock};

use gtk::gdk;
use serde::Deserialize;

use crate::model::{EntryKind, FileEntry};

const RULES: &str = include_str!("../../data/yazi-icons.toml");

#[derive(Deserialize)]
struct Rule {
    name: String,
    text: String,
    fg: String,
}

#[derive(Deserialize)]
struct Rules {
    dirs: Vec<Rule>,
    files: Vec<Rule>,
    exts: Vec<Rule>,
    conds: Vec<Rule>,
}

pub(crate) struct Icon {
    pub(crate) glyph: String,
    pub(crate) color: gdk::RGBA,
}

struct Table {
    dirs: HashMap<String, Icon>,
    files: HashMap<String, Icon>,
    exts: HashMap<String, Icon>,
    conds: HashMap<String, Icon>,
}

fn parse_color(value: &str) -> gdk::RGBA {
    value.parse().unwrap_or(gdk::RGBA::WHITE)
}

fn index(rules: Vec<Rule>, lowercase: bool) -> HashMap<String, Icon> {
    rules
        .into_iter()
        .map(|rule| {
            let key = if lowercase {
                rule.name.to_lowercase()
            } else {
                rule.name
            };
            (
                key,
                Icon {
                    glyph: rule.text,
                    color: parse_color(&rule.fg),
                },
            )
        })
        .collect()
}

fn table() -> &'static Table {
    static TABLE: OnceLock<Table> = OnceLock::new();
    TABLE.get_or_init(|| {
        let rules: Rules = toml::from_str(RULES).expect("bundled yazi icon table");
        Table {
            dirs: index(rules.dirs, false),
            files: index(rules.files, false),
            // Yazi matches extensions case-insensitively.
            exts: index(rules.exts, true),
            conds: index(rules.conds, false),
        }
    })
}

/// Resolves an entry to its icon, following yazi's order: an exact directory or
/// filename first, then the extension, then the generic condition rules.
pub(crate) fn icon_for(entry: &FileEntry) -> Option<&'static Icon> {
    let table = table();
    let name = entry.display_name.as_str();
    let is_dir = matches!(
        entry.kind,
        EntryKind::Directory | EntryKind::DirectorySymbolicLink
    );

    if is_dir {
        return table.dirs.get(name).or_else(|| table.conds.get("dir"));
    }

    if let Some(icon) = table.files.get(name) {
        return Some(icon);
    }
    if let Some(extension) = name.rsplit_once('.').map(|(_, ext)| ext.to_lowercase())
        && let Some(icon) = table.exts.get(&extension)
    {
        return Some(icon);
    }
    if matches!(
        entry.kind,
        EntryKind::FileSymbolicLink | EntryKind::SymbolicLink
    ) {
        return table.conds.get("link").or_else(|| table.conds.get("!dir"));
    }
    table.conds.get("!dir")
}

#[cfg(test)]
mod tests;
