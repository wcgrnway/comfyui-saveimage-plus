import sys
import os
import json
import datetime
import numpy
import re
import time
import glob
from PIL import Image, ExifTags
from PIL.PngImagePlugin import PngInfo
from comfy.cli_args import args


def sanitize_filename(value):
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r'[<>:"/\\|?*]', '_', value)
      
def get_pillow_format(extension):
    return {
        "jpg": "JPEG",
        "png": "PNG",
        "webp": "WEBP"
    }.get(extension.lower(), "PNG")      
      
class SaveImagePlusDynamic:
    def __init__(self):
        pass

    FILE_TYPE_PNG = "PNG"
    FILE_TYPE_JPEG = "JPEG"
    FILE_TYPE_WEBP_LOSSLESS = "WEBP (lossless)"
    FILE_TYPE_WEBP_LOSSY = "WEBP (lossy)"
    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "image"

    pillow_format_map = {
      "png": "PNG",
      "jpg": "JPEG",  # ✅ fix is here
      "webp": "WEBP"
    }

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
            "filepath": (
                "STRING", {
                    "multiline": False,
                    "default": "D:/ComfyExports/[prompt]/[date]/[filename]_[next(3)].png",
                    "tooltip": (
                        "Supports dynamic tokens:\n"
                        "[prompt] – sanitized prompt\n"
                        "[filename] – filename prefix\n"
                        "[time] – current timestamp (YYYYMMDD_HHMMSS)\n"
                        "[time(…)] – custom strftime (e.g. %Y-%m-%d)\n"
                        "[date] – shorthand for [time(%Y-%m-%d)]\n"
                        "[next] or [next(N)] – next available number with optional padding"
                    )
                  }
                ),

                "file_type": ([s.FILE_TYPE_PNG, s.FILE_TYPE_JPEG, s.FILE_TYPE_WEBP_LOSSLESS, s.FILE_TYPE_WEBP_LOSSY],),
                "remove_metadata": ("BOOLEAN", {"default": False}),
                "next_padding": ("INT", {"default": 3, "min": 1, "max": 8}),  
                "prefix": ("STRING", {"default": "image"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            }
        }

    @classmethod  
    def DEFINITION(cls):
       return ( "SaveImagePlusDynamic allows saving images to customizable file paths using tokens. "
                "Supports auto-incremented filenames, dynamic subfolders, and prompt-based organization.\n\n"
                "Available tokens:\n"
                "  [prompt]       – sanitized text prompt\n"
                "  [filename]     – user-defined base filename\n"
                "  [date]         – today's date (YYYY-MM-DD)\n"
                "  [time]         – current timestamp (YYYYMMDD_HHMMSS)\n"
                "  [time(...)]    – custom strftime format, e.g. [time(%Y-%m-%d_%H-%M)]\n"
                "  [next]         – next available file number using node padding setting\n"
                "  [next(N)]      – next available file number with inline N-digit padding\n\n"
                "Example path: output/[prompt]/[date]/img_[next(4)].png"
               )   

    
    def save_images(self, images, filepath, file_type, remove_metadata, next_padding, prefix="image", prompt=None, extra_pnginfo=None):
        extension_map = {
            self.FILE_TYPE_PNG: "png",
            self.FILE_TYPE_JPEG: "jpg",
            self.FILE_TYPE_WEBP_LOSSLESS: "webp",
            self.FILE_TYPE_WEBP_LOSSY: "webp",
        }
        extension = extension_map.get(file_type, "png")
        results = []
        tokens = TokenParser(padding=next_padding)

        if prompt:
          safe_prompt = sanitize_filename(prompt.get("prompt", "")) if isinstance(prompt, dict) else ""
          tokens.add("[prompt]", safe_prompt)
          
        tokens.add("[prefix]", prefix or "image")
        tokens.add("[seed]", str(datetime.datetime.now().microsecond))  # if needed
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        tokens.add("[time]", timestamp)

        counter = 1
        for image in images:
            path_with_tokens = filepath.replace("[counter]", f"{counter:03d}")
            parsed_path = tokens.parse(path_with_tokens)
            parsed_path = os.path.abspath(parsed_path)

            os.makedirs(os.path.dirname(parsed_path), exist_ok=True)

            array = 255. * image.cpu().numpy()
            img = Image.fromarray(numpy.clip(array, 0, 255).astype(numpy.uint8))

            kwargs = {}
            if extension == "png":
                kwargs["compress_level"] = 4
                if not remove_metadata and not args.disable_metadata:
                    metadata = PngInfo()
                    if prompt is not None:
                        metadata.add_text("prompt", json.dumps(prompt))
                    if extra_pnginfo is not None:
                        for x in extra_pnginfo:
                            metadata.add_text(x, json.dumps(extra_pnginfo[x]))
                    kwargs["pnginfo"] = metadata
            else:
                if file_type == self.FILE_TYPE_WEBP_LOSSLESS:
                    kwargs["lossless"] = True
                else:
                    kwargs["quality"] = 90
                if not remove_metadata and not args.disable_metadata:
                    metadata = {}
                    if prompt is not None:
                        metadata["prompt"] = prompt
                    if extra_pnginfo is not None:
                        metadata.update(extra_pnginfo)
                    exif = img.getexif()
                    exif[ExifTags.Base.UserComment] = json.dumps(metadata)
                    kwargs["exif"] = exif.tobytes()

            img.save(parsed_path, **kwargs)
            
            # Create a ComfyUI-compatible preview path
            preview_dir = os.path.join("output", "SaveImagePlusDynamicPreview")
            os.makedirs(preview_dir, exist_ok=True)

            preview_path = os.path.join(preview_dir, os.path.basename(parsed_path))
            pillow_format = self.pillow_format_map.get(extension, "PNG")
            img.save(preview_path, format=pillow_format, **kwargs)

            print(f"[SaveImagePlusDynamic] Saved: {parsed_path}")

            try:
                subfolder = os.path.relpath(os.path.dirname(parsed_path), start=os.path.abspath("output"))
            except ValueError:
                subfolder = os.path.dirname(parsed_path)

            results.append({
               "filename": os.path.basename(preview_path),
               "full_path": preview_path,
               "subfolder": "SaveImagePlusDynamicPreview",
                    "type": "output"
            })
            counter += 1

        return {"ui": {"images": results}}

class TokenParser:
    def __init__(self, tokens=None, padding=3):
        self.tokens = tokens if tokens else {}
        self.padding = padding
    
    def add(self, key, value):
        self.tokens[key] = value

    def parse(self, text):
      
        if "[date]" in text:
            text = text.replace("[date]", datetime.datetime.now().strftime("%Y-%m-%d"))
        # Handle [time(%Y-%m-%d_%H-%M-%S)]
        time_matches = re.findall(r"\[time\((.*?)\)\]", text)
        for fmt in time_matches:
            formatted = datetime.datetime.now().strftime(fmt)
            text = text.replace(f"[time({fmt})]", formatted)

        # Handle [time] fallback
        if "[time]" in text:
            text = text.replace("[time]", datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))

        # Handle all other tokens
        for token, value in self.tokens.items():
            text = text.replace(token, str(value))

        if re.search(r"\[next(?:\(\d+\))?\]", text):
            text = self.resolve_next_file_number(text, self.padding)
            
        return text

    def resolve_next_file_number(self, text, default_padding):
        """
        Look for files matching the same pattern and return next unused number.
        """
        match = re.search(r"\[next(?:\((\d+)\))?\]", text)
        if not match:
            return text

        full_token = match.group(0)         # e.g. [next(4)] or [next]
        custom_pad = match.group(1)         # e.g. 4 or None
        padding = int(custom_pad) if custom_pad else default_padding
        pattern_path = text.replace(full_token, "*")

        import os

        # Create a wildcard version of the filename
        folder = os.path.dirname(pattern_path)
        base = os.path.basename(pattern_path)

        existing_files = glob.glob(os.path.join(folder, base))
        max_num = 0
        print(f"Scanning {folder}/{base}")

        for f in existing_files:
            num_match = re.search(r"(\d+)(?=\.\w+$)", f)
            if num_match:
                num = int(num_match.group(1))
                max_num = max(max_num, num)

        next_num = max_num + 1
        return text.replace(full_token, f"{next_num:0{padding}d}")
      

          
# ComfyUI registration
NODE_CLASS_MAPPINGS = {
    "SaveImagePlusDynamic": SaveImagePlusDynamic
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImagePlusDynamic": "💾 Save Image Plus Dynamic"
}
