#!/bin/bash

# Function to find all dist-packages directories in the system
find_dist_packages() {
    python3 -c "import site; print('\n'.join([p for p in site.getsitepackages() if 'dist-packages' in p]))"
}

# Function to find the site-packages directory in a virtual environment, if active
find_venv_packages() {
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "Virtual environment detected: $VIRTUAL_ENV"
        python3 -c "import site; print(site.getsitepackages()[0])"
    else
        echo "No active virtual environment."
    fi
}

# Function to remove files related to specific packages
remove_installed_files() {
    local package_names=("$@")
    
    # Get system dist-packages paths
    local dist_packages_paths=$(find_dist_packages)
    
    # Get virtual environment site-packages path if venv is active
    local venv_packages_path=$(find_venv_packages)

    # Combine both dist-packages and venv site-packages into one list
    all_package_paths="$dist_packages_paths $venv_packages_path"

    if [ -z "$all_package_paths" ]; then
        echo "No package directories found."
        return
    fi

    for package_name in "${package_names[@]}"; do
        for path in $all_package_paths; do
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
