import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse

import requests

# Constants for the script
DIRECTORY = "docs/tools/vdb_table/data"

GITHUB_API_URL = "https://api.github.com/repos/"
DOCKER_HUB_API_URL = "https://hub.docker.com/v2/repositories/"
NPM_API_URL = "https://api.npmjs.org/downloads/point/"


def get_github_stars(github_url, headers=None):
    global GITHUB_API_URL
    parts = github_url.split("/")
    owner_repo = "/".join(parts[-2:])
    response = requests.get(f"{GITHUB_API_URL}{owner_repo}", headers=headers)
    if response.status_code == 200:
        return response.json()["stargazers_count"]
    else:
        print(f"Failed to fetch stars for {github_url}: {response.status_code}")
        return None


def get_docker_pulls(namespace, repo_name, headers=None):
    global DOCKER_HUB_API_URL
    response = requests.get(
        f"{DOCKER_HUB_API_URL}{namespace}/{repo_name}/", headers=None
    )
    if response.status_code == 200:
        return response.json()["pull_count"]
    else:
        print(
            f"Failed to fetch pulls for {namespace}/{repo_name}: {response.status_code}"
        )
        return None


def get_npm_package_info(npm_package):
    response = requests.get(f"https://registry.npmjs.org/{npm_package}")
    print(f"https://registry.npmjs.org/{npm_package}")
    if response.status_code == 200:
        data = response.json()
        first_release_date = data.get("time")['created']
        return first_release_date
    else:
        print(
            f"Failed to fetch npm package info for {npm_package}: {response.status_code}"
        )
        return None


def get_npm_downloads(npm_package, headers=None, start_date=None):
    if start_date is None:
        release_date = get_npm_package_info(npm_package)
        if release_date:
            # Subtract one day from the release date for the start range
            start_date = datetime.strptime(release_date, "%Y-%m-%dT%H:%M:%S.%fZ") - timedelta(days=1)

    start_date = start_date.strftime("%Y-%m-%d")
    end_date = (datetime.now() + + timedelta(days=1)).strftime("%Y-%m-%d")
    response = requests.get(f"{NPM_API_URL}{start_date}:{end_date}/{npm_package}")
    if response.status_code == 200:
        return response.json()["downloads"]
    else:
        print(
            f"Failed to fetch npm downloads for {npm_package}: {response.status_code}"
        )
        return None


def update_json_files(directory, headers=None):
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            file_path = os.path.join(directory, filename)
            with open(file_path, "r+", encoding="utf-8") as json_file:
                data = json.load(json_file)
                github_url = data.get("github_stars", {}).get("source_url", "")
                dockerhub_url = data.get("docker_pulls", {}).get("source_url", "")
                npm_url = data.get("npm_downloads", {}).get("source_url", "")
                if dockerhub_url:
                    parsed_dockerhub_path = str(urlparse(dockerhub_url).path)
                    docker_namespace = (
                        list(parsed_dockerhub_path.strip().split("/"))[-2]
                        if "/_/" not in parsed_dockerhub_path
                        else "library"
                    )
                    docker_repo_name = list(parsed_dockerhub_path.strip().split("/"))[
                        -1
                    ]
                    pulls = get_docker_pulls(docker_namespace, docker_repo_name)
                    if pulls is not None:
                        data["docker_pulls"]["value"] = pulls
                if github_url:
                    stars = get_github_stars(github_url, headers)
                    if stars is not None:
                        data["github_stars"]["value"] = stars
                if npm_url:
                    npm_package_name = list(npm_url.split('https://www.npmjs.com/package/'))[1].strip()
                    downloads = get_npm_downloads(npm_package_name, headers)
                    if downloads is not None:
                        data["npm_downloads"]["value"] = downloads

                    start_date = datetime.now() - timedelta(days=90)
                    downloads = get_npm_downloads(npm_package_name, headers, start_date)
                    if downloads is not None:
                        data["npm_downloads"]["value_90_days"] = downloads

                # Write the updated data back to the file
                json_file.seek(0)  # Rewind to the start of the file
                json.dump(data, json_file, indent=2)
                json_file.truncate()  # Remove any leftover content


if __name__ == "__main__":
    update_json_files(DIRECTORY)
