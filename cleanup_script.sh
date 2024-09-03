#!/bin/bash

# Function to find all dist-packages directories
find_dist_packages() {
    python3 -c "import site; print('\n'.join([p for p in site.getsitepackages() if 'dist-packages' in p]))"
}

# Function to remove files related to specific packages
remove_installed_files() {
    local package_names=("$@")
    local dist_packages_paths=$(find_dist_packages)

    if [ -z "$dist_packages_paths" ]; then
        echo "No dist-packages directories found."
        return
    fi

    for package_name in "${package_names[@]}"; do
        for path in $dist_packages_paths; do
            package_path="$path/$package_name"
            egg_info_path="$path/${package_name//-/_}.egg-info"

            if [ -d "$package_path" ]; then
                echo "Removing installed files from $package_path..."
                sudo rm -rf "$package_path"
            else
                echo "No installed files found for package '$package_name' in $path"
            fi

            if [ -d "$egg_info_path" ]; then
                echo "Removing $egg_info_path..."
                sudo rm -rf "$egg_info_path"
            fi
        done
    done
}

# Function to clean up build artifacts
clean_build_artifacts() {
    echo "Cleaning build artifacts..."
    sudo rm -rf build/ dist/ *.egg-info
}

# Define the package names to search and remove
PACKAGE_NAMES=("palaidn" "palaidn-subnet" "palaidn_subnet")

# Remove installed files for each package
remove_installed_files "${PACKAGE_NAMES[@]}"

# Clean up build artifacts
clean_build_artifacts

echo "Cleanup complete."