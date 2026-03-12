import os


def apply_patch(repo_path, file, new_code):

    try:
        file_path = os.path.join(repo_path, file)

        if not os.path.exists(file_path):
            return {"success": False, "error": "File not found"}

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_code)

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}