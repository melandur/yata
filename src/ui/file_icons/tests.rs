// SPDX-License-Identifier: MIT

use super::*;
use crate::model::{Location, MetadataValue};
use std::{ffi::OsString, path::PathBuf};

fn entry(name: &str, kind: EntryKind) -> FileEntry {
    FileEntry {
        location: Location::local(PathBuf::from("/tmp").join(name)),
        thumbnail_path: None,
        native_name: OsString::from(name),
        display_name: name.to_owned(),
        kind,
        size: MetadataValue::Unknown,
        modified_unix_seconds: MetadataValue::Unknown,
        mode: MetadataValue::Unknown,
        image_dimensions: MetadataValue::Unknown,
        child_count: MetadataValue::Unknown,
        duration_seconds: MetadataValue::Unknown,
        is_hidden: false,
    }
}

#[test]
fn an_exact_filename_beats_its_extension() {
    let by_name = icon_for(&entry(".gitlab-ci.yml", EntryKind::File)).expect("filename rule");
    let by_ext = icon_for(&entry("other.yml", EntryKind::File)).expect("extension rule");
    assert_ne!(by_name.glyph, by_ext.glyph);
}

#[test]
fn extensions_match_regardless_of_case() {
    let lower = icon_for(&entry("photo.png", EntryKind::File)).expect("extension rule");
    let upper = icon_for(&entry("photo.PNG", EntryKind::File)).expect("extension rule");
    assert_eq!(lower.glyph, upper.glyph);
}

#[test]
fn known_directories_keep_their_own_icon() {
    let downloads = icon_for(&entry("Downloads", EntryKind::Directory)).expect("directory rule");
    let plain = icon_for(&entry("src", EntryKind::Directory)).expect("generic directory");
    assert_ne!(downloads.glyph, plain.glyph);
}

#[test]
fn every_entry_resolves_to_some_icon() {
    for kind in [
        EntryKind::File,
        EntryKind::Directory,
        EntryKind::FileSymbolicLink,
        EntryKind::DirectorySymbolicLink,
    ] {
        assert!(
            icon_for(&entry("no-extension-here", kind)).is_some(),
            "{kind:?}"
        );
    }
}
