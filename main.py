import os
import re
import requests
import hashlib
import markdownify


def format_storage_hash(string, length):
    """
    Format a received string to ensure it doesnt contain any illegal characters (Windows)
    and cut it to the specified length.
    """
    # Define the pattern for illegal characters
    pattern = r"[^0-9a-zA-Z_\-]"

    # Replace all matches with an underscore
    temp_string = re.sub(pattern, '_', string)

    # Truncate the string to the specified length
    return temp_string[:length]


# model-versions by hash API endpoint URL
api_endpoint = "https://civitai.com/api/v1/model-versions/by-hash/"

# model API
api_endpoint_model = "https://civitai.com/api/v1/models/"

# Folder path where the models,etc. are located
# folder_path = f"F:\\automatic1111\\stable-diffusion-webui\\models\\Stable-diffusion\\"
folder_path = f"F:\\automatic1111\\stable-diffusion-webui\\models\\Lora\\"

# Ignore existing folders, force renew.
# If set to true, it will update the folders, regardless if they exist already or not.
force_update = False

# Download previews for entire Model
# If set to false it will only download previews associated with the current version, true will dwld all versions.
check_entire_model = True

# Iterate over all files in the folder
filenames = os.listdir(folder_path)
counter = 0
for filename in filenames:
    counter += 1
    if not (filename.endswith(".ckpt") or filename.endswith(".safetensors")):
        continue
    print(f"Processing file ({counter}/{len(filenames)}) {filename}")
    file_path = os.path.join(folder_path, filename)

    # Check if previews already exist.
    file_noext = os.path.splitext(filename)[0]
    folder_name = os.path.join(folder_path, "Previews", file_noext)  # This uses the name of the file
    if (not force_update) and os.path.exists(folder_name):
        continue

    # Compute SHA256 hash of the file
    try:
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        print(f"Error computing hash of file {filename}: {e}")
        continue

    # Construct API URL with the file hash
    api_url = api_endpoint + file_hash

    # Make GET request to the API
    try:
        response = requests.get(api_url)
        description = response.json()["description"]
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error making API request for file {filename}: {e}")
        continue
    except KeyError as e:
        print(f"Missing value from response for file {filename}: {e}")
        continue

    # Extract model and name fields from the API response, only use if you want names according to the API response.
    # try:
    #     model_name = response.json()["model"]["name"]
    #     version_name = response.json()["name"]
    # except (KeyError, TypeError) as e:
    #     print(f"Error extracting model and version name from API response for file {filename}: {e}")
    #     continue

    # If check the entire model, it will grab all previews from all model versions.
    if check_entire_model:
        api_url = api_endpoint_model + str(response.json()["modelId"])
        try:
            response = requests.get(api_url)
            description = response.json()["description"]
            images = enumerate([image for version in response.json()['modelVersions'] for image in version['images']])
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error making API request for file {filename}: {e}")
            continue
        except KeyError as e:
            print(f"Missing value from response for file {filename}: {e}")
            continue
    else:
        images = enumerate(response.json()["images"])

    # Create folder with A_B name
    # folder_name = os.path.join(folder_path, "Previews", f"{model_name}_{version_name}") This uses the name from the API response
    os.makedirs(folder_name, exist_ok=True)

    # Store model description, converts html to markdown
    md_file_name = f"{file_noext}.md"
    md_description = markdownify.markdownify(description, headint_style="ATX")
    try:
        with open(os.path.join(folder_name, md_file_name), "wb") as f:
            f.write(md_description.encode())
    except Exception as e:
        print(f"Error saving description for file {filename}: {e}")
        continue

    # Save all photos in the folder
    for i, image in images:
        #  image_url = image["url"].replace("/width=", f"/width={image['width']}")
        url = re.sub(r'/width=\d+/', f'/width={image["width"]}/', image["url"])
        try:
            image_response = requests.get(url)
            image_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error downloading image {i} for file {filename}: {e}")
            continue

        formatted_hash = format_storage_hash(image["hash"], 32)

        # Save image to file
        # image_file_name = f"image_{i}.png" #  Use incremental number to store image
        image_file_name = f"{i}_{file_noext}.{formatted_hash}.png"  # Use hash to store image, i to keep order.
        try:
            with open(os.path.join(folder_name, image_file_name), "wb") as f:
                f.write(image_response.content)
        except Exception as e:
            print(f"Error saving image {i} for file {filename}: {e}")
            continue

print("Finished processing all files.")
