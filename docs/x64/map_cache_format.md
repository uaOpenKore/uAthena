# Map Cache Serialization Format

## Version 1 (legacy)

* **Header** (`struct map_cache_disk_header_v1`)
  * `sizeof_header` (`uint32_t`) – size of header (16 bytes).
  * `sizeof_map` (`uint32_t`) – size of each entry (56 bytes).
  * `nmaps` (`uint32_t`) – number of entries.
  * `filesize` (`uint32_t`) – total file size in bytes.
* **Entry** (`struct map_cache_disk_entry_v1`)
  * `fn[32]` – map name.
  * `xs`, `ys` (`uint32_t`) – map dimensions.
  * `water_height` (`int32_t`) – water level.
  * `pos` (`uint32_t`) – offset of payload.
  * `compressed` (`uint32_t`) – 0 for raw GAT, 1 for zlib payload.
  * `compressed_len` (`uint32_t`) – compressed byte length (only valid when `compressed` is 1).
* **Payload**
  * Stored directly after the directory (`sizeof_header + sizeof_map * nmaps`).
  * Offsets and lengths are limited to 32-bit values.

## Version 2 (current)

* **Header** (`struct map_cache_disk_header_v2`)
  * `magic` (`uint32_t`) – constant `0x4D434143` (`"MCAC"`).
  * `version` (`uint32_t`) – constant `2`.
  * `header_size` (`uint32_t`) – size of header (32 bytes).
  * `entry_size` (`uint32_t`) – size of each entry (64 bytes).
  * `entry_count` (`uint32_t`) – number of directory entries.
  * `reserved` (`uint32_t`) – currently zero.
  * `filesize` (`uint64_t`) – total file size in bytes.
* **Entry** (`struct map_cache_disk_entry_v2`)
  * `fn[32]` – map name.
  * `xs`, `ys` (`uint32_t`), `water_height` (`int32_t`).
  * `compressed` (`uint32_t`).
  * `pos` (`uint64_t`) – payload offset.
  * `compressed_len` (`uint64_t`) – payload length when compressed.
* **Payload**
  * Directory sits at `header_size + entry_size * entry_count`.
  * Offsets and lengths are 64-bit to accommodate large cache files.

## Migration Strategy

1. Read legacy header and entries.
2. Copy payload data to a temporary file while tracking new offsets.
3. Emit a version-2 header and directory with updated offsets and lengths.
4. Replace the original file with the upgraded copy.

The map server automatically upgrades legacy files on load and always writes version 2.
