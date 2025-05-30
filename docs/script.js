// Global variable declarations
let fileListDiv;
let breadcrumbsDiv;
let loadingIndicator;
let allData = []; // To store the parsed JSON data from onedrive_index.json
let currentPathSegments = []; // Array of strings representing the current folder path

// init function
function init() {
    fileListDiv = document.getElementById('file-list');
    breadcrumbsDiv = document.getElementById('breadcrumbs');
    loadingIndicator = document.getElementById('loading-indicator');

    if (!fileListDiv || !breadcrumbsDiv || !loadingIndicator) {
        console.error("Required DOM elements not found. Check your HTML IDs.");
        return;
    }
    fetchData();
}

// fetchData function
async function fetchData() {
    if (loadingIndicator) loadingIndicator.style.display = 'block';
    if (fileListDiv) fileListDiv.innerHTML = ''; // Clear previous list

    try {
        const response = await fetch('./onedrive_index.json'); // Assumes onedrive_index.json is in the same folder
        if (!response.ok) {
            throw new Error(`Failed to fetch onedrive_index.json: ${response.status} ${response.statusText}`);
        }
        allData = await response.json();
        if (!Array.isArray(allData)) {
            console.error("onedrive_index.json is not a valid array. Root must be an array of items.");
            allData = []; // Reset to empty to prevent further errors
        }
    } catch (error) {
        console.error("Error fetching or parsing OneDrive index data:", error);
        if (fileListDiv) fileListDiv.innerHTML = '<p style="color: red;">Error loading file data. Please try again later.</p>';
        allData = []; // Ensure allData is an empty array on error
    } finally {
        if (loadingIndicator) loadingIndicator.style.display = 'none';
    }
    
    // Initial render
    currentPathSegments = []; // Start at root
    const rootData = getDataByPath(currentPathSegments);
    renderFileList(rootData);
    updateBreadcrumbs(currentPathSegments);
}

// renderFileList function
function renderFileList(items) {
    if (!fileListDiv) return;
    fileListDiv.innerHTML = ''; // Clear previous list

    if (!items || items.length === 0) {
        const emptyMessage = document.createElement('p');
        emptyMessage.textContent = 'This folder is empty.';
        emptyMessage.style.textAlign = 'center';
        emptyMessage.style.padding = '20px';
        fileListDiv.appendChild(emptyMessage);
        return;
    }

    items.forEach(item => {
        const listItem = document.createElement('div');
        listItem.classList.add('list-item');
        listItem.classList.add(item.type === 'folder' ? 'folder-item' : 'file-item');
        listItem.dataset.name = item.name; // Store name for navigation
        // listItem.dataset.id = item.id; // ID might be useful later

        const itemIcon = document.createElement('span');
        itemIcon.classList.add('item-icon');
        // Icons are added by CSS using .folder-item .item-icon::before or .file-item .item-icon::before

        const itemName = document.createElement('span');
        itemName.classList.add('item-name');
        itemName.textContent = item.name;

        listItem.appendChild(itemIcon);
        listItem.appendChild(itemName);

        if (item.type === 'folder') {
            listItem.addEventListener('click', () => {
                // currentPathSegments is already up-to-date from where this item was rendered
                navigateToFolder(item.name);
            });
        } else { // 'file'
            listItem.addEventListener('click', () => {
                if (item.webUrl) {
                    window.open(item.webUrl, '_blank');
                } else {
                    console.warn("File item has no webUrl:", item);
                    alert("This file cannot be opened as its web URL is missing.");
                }
            });
        }
        fileListDiv.appendChild(listItem);
    });
}

// navigateToFolder function (handles click on a folder in the current view)
function navigateToFolder(folderName) {
    // folderName is the name of the folder clicked in the current view.
    // currentPathSegments should represent the path to the *parent* of folderName.
    const newPathSegments = [...currentPathSegments, folderName];
    const folderData = getDataByPath(newPathSegments);

    if (folderData) { // Check if folderData is valid (not an empty array from a bad path)
        currentPathSegments = newPathSegments; // Update global path
        renderFileList(folderData);
        updateBreadcrumbs(currentPathSegments);
    } else {
        console.error(`Could not navigate to folder: ${folderName}. Data not found at path: ${newPathSegments.join('/')}`);
        // Optionally, display an error to the user
    }
}

// updateBreadcrumbs function
function updateBreadcrumbs(pathSegments) {
    if (!breadcrumbsDiv) return;
    breadcrumbsDiv.innerHTML = ''; // Clear previous breadcrumbs

    // Home link
    const homeLink = document.createElement('a');
    homeLink.textContent = 'Home';
    homeLink.href = '#'; // Prevent page reload
    homeLink.addEventListener('click', (e) => {
        e.preventDefault();
        currentPathSegments = [];
        renderFileList(getDataByPath(currentPathSegments));
        updateBreadcrumbs(currentPathSegments);
    });
    breadcrumbsDiv.appendChild(homeLink);

    // Path segment links
    let accumulatedPath = [];
    pathSegments.forEach((segment, index) => {
        const separator = document.createElement('span');
        separator.textContent = ' / ';
        separator.style.margin = '0 5px'; // Add some spacing around separator
        breadcrumbsDiv.appendChild(separator);

        const segmentLink = document.createElement('a');
        segmentLink.textContent = segment;
        
        // If it's the last segment (current folder), make it non-interactive or styled differently
        if (index === pathSegments.length - 1) {
            segmentLink.classList.add('current-breadcrumb');
            segmentLink.style.color = '#333'; // Example: different color for current
            segmentLink.style.fontWeight = 'bold';
            // segmentLink.removeAttribute('href'); // Or remove href
        } else {
            segmentLink.href = '#'; // Prevent page reload
            const pathForThisSegment = [...pathSegments.slice(0, index + 1)];
            segmentLink.addEventListener('click', (e) => {
                e.preventDefault();
                currentPathSegments = pathForThisSegment;
                renderFileList(getDataByPath(currentPathSegments));
                updateBreadcrumbs(currentPathSegments);
            });
        }
        breadcrumbsDiv.appendChild(segmentLink);
    });
}

// getDataByPath function
function getDataByPath(pathSegments) {
    if (!pathSegments || pathSegments.length === 0) {
        return allData; // Return the root data (the whole array)
    }
    let currentLevelData = allData;
    for (const segment of pathSegments) {
        const foundFolder = currentLevelData.find(item => item.type === 'folder' && item.name === segment);
        if (foundFolder && foundFolder.children) {
            currentLevelData = foundFolder.children;
        } else {
            // Path segment not found, or item is not a folder, or folder has no children attribute
            console.warn(`Path segment "${segment}" not found or item is not a folder with children in path: ${pathSegments.join('/')}`);
            return []; // Return empty array to signify path not resolving to a valid folder content
        }
    }
    return currentLevelData; // This will be an array of items (children of the last segment)
}

// Attach init to DOMContentLoaded
document.addEventListener('DOMContentLoaded', init);
