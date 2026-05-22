# Local Library and Matching

## Purpose

The matching workflow connects remote playlist knowledge to playable audio files in a
local environment such as a USB drive or music folder.

The matching model should be conservative. The same title and artist are not enough to
prove two records are the same song when different mixes, edits, remixes, or bootlegs
may exist.

## Local Environment Scan

The user should be able to choose a root folder or USB drive. The app scans supported
audio files and records:

- path;
- filename;
- extension;
- file size;
- modification time;
- embedded title, artist, album, duration, BPM, key, and comments where available.

## Matching Pipeline

The first version can use a staged matching approach:

1. Exact normalized title and artist match.
2. Title and artist match with punctuation, casing, and common suffixes normalized.
3. Duration-tolerant match when remote and local durations are available.
4. Filename heuristic match.
5. Manual user mapping.

Future versions may add audio fingerprints.

Automatic matching should only accept a match when the system is confident that the
remote song and local audio file represent the same mix/version. Otherwise the item
should enter manual review.

## Match States

Each canonical song should have a clear local-audio status:

- matched: one accepted local audio file exists;
- missing audio: no plausible local audio file exists;
- ambiguous: multiple plausible local audio files exist;
- manually mapped: the user selected the correct local file;
- unmatched candidate: a local file exists but has not been linked to any managed song.

## Missing Audio

The app must highlight songs that appear in one or more playlists but have no local
audio file. The dashboard should show missing audio by playlist and globally.

Example:

- Song X is present in Playlist Y.
- No matching local audio file is found.
- Song X is shown as missing audio for Playlist Y and for the global library.

## Manual Mapping

The user must be able to map a remote song to an unmatched local file.

Example:

- Song X is missing according to automatic matching.
- The user finds a local file named `artist - track club edit.mp3`.
- The user links that file to Song X.
- The app stores the relationship as a manual MatchLink.

Manual mappings should be trusted more than future automatic guesses unless the file
disappears.

The review workflow should let the user play local candidate files before accepting a
mapping. If another local file is already mapped or a candidate needs comparison, the
UI should make it easy to play and compare the available local audio files.

## Unmanaged Local Files

The app must also track local audio files that are present in the selected environment
but not present in any imported playlist.

These files are useful because they may be:

- songs the user forgot to add to playlists;
- old exports;
- duplicates;
- unrelated local files;
- candidates for manual mapping.
