# Save Image Plus for ComfyUI

- This custom node is largely identical to the usual Save Image but allows saving images also in JPEG and WEBP formats, the latter with both lossless and lossy compression.
- Metadata is embedded in the images for loading workflows.
- An option to remove metadata is available and can be overridden from the node; otherwise, it defaults to the ComfyUI arguments.

![Screenshot 2024-05-30 at 10 06 54](https://github.com/Goktug/comfyui-saveimage-plus/assets/534426/d08bb984-911e-4a3c-a5cc-7a069cdc7005)


## Installation

To install, clone this repository into the `ComfyUI/custom_nodes` folder with:

```sh
git clone https://github.com/Goktug/comfyui-saveimage-plus
```

## 🔧 SaveImagePlusDynamic Node (Enhanced)

This version of SaveImagePlus has been extended to support:

  CROSS DRIVE SUPPORT!  You can save in a different drive than where ComfyUI is installed.
  
  Note: To maintain preview capabilities a duplicate file is stored in the ComfyUI 
        output folder ./SaveImagePlusDynamicPreview/. So, you will have to clear that
        folder periodically.

- Dynamic output paths using tokens (e.g. `[prompt]`, `[date]`, `[next]`)
- Optional `[next(N)]` auto-incremented filenames with padding
- Dual-save support for UI preview and cross-drive exports
- Custom token parser and safer filename sanitization
- Improved time-based formatting and collision avoidance

### Supported Tokens

| Token          | Description                               |
|----------------|-------------------------------------------|
| `[prompt]`     | The sanitized text prompt                 |
| `[filename]`   | User-defined name                         |
| `[date]`       | Today's date in YYYY-MM-DD                |
| `[time]`       | Timestamp in YYYYMMDD_HHMMSS              |
| `[time(...)]`  | Custom strftime format                    |
| `[next]`       | Next available number with node padding   |
| `[next(N)]`    | Same, with inline padding override        |

### Example Output Path

D:/Promo/Character Portaits/scratch_ai/std/[date]/[prefix]_[next].png

