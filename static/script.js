// weave_webapp/static/script.js

// weave_webapp/static/script.js

document.addEventListener('DOMContentLoaded', () => {
    // Aggressive cleanup for old static "All" buttons from cached HTML
    let oldBtnTag = document.getElementById('select-all-tags');
    if (oldBtnTag && oldBtnTag.parentElement && oldBtnTag.parentElement.id !== 'tag-toggles') {
        if (oldBtnTag.parentElement.classList.contains('toggle-header')) {
            oldBtnTag.parentElement.remove(); // Remove the whole old header
        } else {
            oldBtnTag.remove(); // Otherwise just remove the button itself
        }
    }
    let oldBtnPerson = document.getElementById('select-all-people');
    if (oldBtnPerson && oldBtnPerson.parentElement && oldBtnPerson.parentElement.id !== 'person-toggles') {
         if (oldBtnPerson.parentElement.classList.contains('toggle-header')) {
            oldBtnPerson.parentElement.remove(); // Remove the whole old header
        } else {
            oldBtnPerson.remove(); // Otherwise just remove the button itself
        }
    }

    // --- DOM Elements ---
    const originalSujetSpan = document.getElementById('original-sujet');
const displaySujetIdSpan = document.getElementById('display-sujet-id'); // Added for separate ID display
    const aiSuggestionSpan = document.getElementById('ai-suggestion');
    const viewCountSpan = document.getElementById('view-count');
    const currentStatusSpan = document.getElementById('current-status');
    const userNotesTextarea = document.getElementById('user-notes');
    const userTagsInput = document.getElementById('user-tags');
    const tagTogglesDiv = document.getElementById('tag-toggles');
    const personTogglesDiv = document.getElementById('person-toggles');
    const sujetCountDisplay = document.getElementById('sujet-count-display');
    const modeToggleRadios = document.querySelectorAll('input[name="edit-mode"]');

    const saveButton = document.getElementById('save-button');
    const skipButton = document.getElementById('skip-button');
    const backButton = document.getElementById('back-button');
    const deleteButton = document.getElementById('delete-button');
    const reverseSortButton = document.getElementById('reverse-sort-button');
        const quickSparkButton = document.getElementById('quick-spark-button');
    const firstSujetButton = document.getElementById('first-sujet-button');
    const lastSujetButton = document.getElementById('last-sujet-button');

    const sujetContentDiv = document.getElementById('sujet-content');
    const noMoreSujetsDiv = document.getElementById('no-more-sujets');

    // --- State Variables ---
    let currentSujetId = null;
    let currentSujetData = null;
    let currentOffset = 0;
    const history = [];
    const historySize = 10;
    let editMode = 'filter'; // 'filter' or 'tag'
    let activeFilterState = { tags: [], people: [] };

    // Abbreviated tag display mapping for mobile compactness
    const tagAbbreviations = {
        'AI': 'AI',
        'Work': 'Wrk',
        'Medical': 'Med',
        'Science': 'Sci',
        'History': 'Hist',
        'Politics': 'Pol',
        'Culture': 'Cult',
        'Sports': 'Sprt',
        'Travel': 'Trvl',
        'Food & Drink': 'Food',
        'Observation': 'Obs',
        'Quote': 'Qte',
        'People': 'Ppl',
        'Idea/Project': 'Idea'
    };

    const predefinedTags = [
        'AI', 'Work', 'Medical', 'Science', 'History', 'Politics', 'Culture',
        'Sports', 'Travel', 'Food & Drink', 'Observation', 'Quote', 'People', 'Idea/Project'
    ];
    // Abbreviation for people toggles
const personAbbreviations = {
    'work': 'wrk'
};
const predefinedPeople = ['S', 'Fam', 'Stef', 'MD', 'AK', 'ML', 'work'];

    // --- Utility Functions ---

    function updateGlobalButtonStates(sujetIsLoaded, currentHistoryLength) {
        saveButton.disabled = !sujetIsLoaded;
        skipButton.disabled = !sujetIsLoaded;
        deleteButton.disabled = !sujetIsLoaded;
        backButton.disabled = currentHistoryLength <= 1;
        quickSparkButton.disabled = false; // Always enabled
        reverseSortButton.disabled = false; // Always enabled
        // Add any other global buttons here if their state depends on sujetIsLoaded or history
    }

    function parseCsvString(csvString) {
        if (!csvString) return [];
        return csvString.split(',').map(item => item.trim().toLowerCase()).filter(Boolean);
    }

    // --- Core Rendering and UI Update Functions ---

    function renderToggles(container, items, type) {
        // Remove any pre-existing Select All button to prevent duplicates
        const existingAllBtn = container.querySelector('.select-all-button');
        if (existingAllBtn) existingAllBtn.remove();
        container.innerHTML = '';
        items.forEach(item => {
            if (!item) return;
            const button = document.createElement('button');
            if (type === 'tag' && tagAbbreviations[item]) {
                button.textContent = tagAbbreviations[item];
                button.title = item;
            } else if (type === 'person' && personAbbreviations[item]) {
                button.textContent = personAbbreviations[item];
                button.title = item;
            } else {
                button.textContent = item.trim();
            }
            button.classList.add(`${type}-toggle`);
            button.dataset.value = item.trim().toLowerCase();
            button.addEventListener('click', handleToggleClick);
            container.appendChild(button);
        });
        // Add Select All button at the end
        const selectAllBtn = document.createElement('button');
        selectAllBtn.className = 'select-all-button';
        selectAllBtn.textContent = 'All';
        if (type === 'tag') {
            selectAllBtn.id = 'select-all-tags';
            selectAllBtn.onclick = () => {
                const allBtns = container.querySelectorAll('.tag-toggle');
                const anyInactive = Array.from(allBtns).some(btn => !btn.classList.contains('active'));
                allBtns.forEach(btn => btn.classList.toggle('active', anyInactive));
                if (editMode === 'filter') updateActiveFilterStateFromUI();
                else updateSujetDataFromToggles();
            };
        } else if (type === 'person') {
            selectAllBtn.id = 'select-all-people';
            selectAllBtn.onclick = () => {
                const allBtns = container.querySelectorAll('.person-toggle');
                const anyInactive = Array.from(allBtns).some(btn => !btn.classList.contains('active'));
                allBtns.forEach(btn => btn.classList.toggle('active', anyInactive));
                if (editMode === 'filter') updateActiveFilterStateFromUI();
                else updateSujetDataFromToggles();
            };
        }
        container.appendChild(selectAllBtn);
    }

    function handleToggleClick(event) {
        const button = event.target;
        const value = button.dataset.value;

        if (editMode === 'filter') {
            button.classList.toggle('active');
            updateActiveFilterStateFromUI();
            currentOffset = 0; // Reset offset to search from beginning with new filters
            // history.length = 0; // DO NOT clear history here. Let 'Back' work to previous filter state.
            updateSujetCount();
            loadNextSujet();
        } else { // 'tag' mode
            if (!currentSujetData) return;
            button.classList.toggle('active');
            updateSujetDataFromToggles();
        }
    }

    function updateActiveFilterStateFromUI() {
        const activeTags = Array.from(tagTogglesDiv.querySelectorAll('.tag-toggle.active')).map(btn => btn.dataset.value);
        const activePeople = Array.from(personTogglesDiv.querySelectorAll('.person-toggle.active')).map(btn => btn.dataset.value);
        activeFilterState = { tags: activeTags, people: activePeople };
    }

    function updateSujetDataFromToggles() {
        if (!currentSujetData) return;

        const activeTags = Array.from(tagTogglesDiv.querySelectorAll('.tag-toggle.active')).map(btn => {
            // Use the full name from the title if it exists (for abbreviations), otherwise use textContent
            return btn.title || btn.textContent.trim();
        });

        const activePeople = Array.from(personTogglesDiv.querySelectorAll('.person-toggle.active')).map(btn => {
            return btn.title || btn.textContent.trim();
        });

        userTagsInput.value = activeTags.join(', ');
        currentSujetData.person = activePeople.join(', ');
    }

    function updateToggleAppearance() {
        if (editMode === 'filter') {
            document.querySelectorAll('.tag-toggle').forEach(btn => {
                btn.classList.toggle('active', activeFilterState.tags.includes(btn.dataset.value));
            });
            document.querySelectorAll('.person-toggle').forEach(btn => {
                btn.classList.toggle('active', activeFilterState.people.includes(btn.dataset.value));
            });
        } else { // 'tag' mode
            if (!currentSujetData) return;
            const sujetTags = parseCsvString(userTagsInput.value);
            const sujetPeople = parseCsvString(currentSujetData.person);
            document.querySelectorAll('.tag-toggle').forEach(btn => {
                btn.classList.toggle('active', sujetTags.includes(btn.dataset.value));
            });
            document.querySelectorAll('.person-toggle').forEach(btn => {
                btn.classList.toggle('active', sujetPeople.includes(btn.dataset.value));
            });
        }
    }

    function displaySujet(sujet) {
        currentSujetId = sujet.id;
        currentSujetData = sujet;
        // Parse ID and Title from sujet.original_sujet (e.g., "ID: 123 - Title Text")
        const match = sujet.original_sujet.match(/^ID:\s*(\d+)\s*-\s*(.*)$/);
        if (match && match[1] && match[2]) {
            displaySujetIdSpan.textContent = match[1]; // Just the ID number
            originalSujetSpan.textContent = match[2]; // Just the Title text
        } else {
            // Fallback if parsing fails, though this shouldn't happen with consistent data
            displaySujetIdSpan.textContent = sujet.id; // Use sujet.id as a fallback for the number
            originalSujetSpan.textContent = sujet.original_sujet; // Show the original string as fallback title
        }

        aiSuggestionSpan.textContent = sujet.ai_suggestion;
        viewCountSpan.textContent = sujet.view_count;
        currentStatusSpan.textContent = sujet.status;
        userNotesTextarea.value = sujet.user_notes || '';
        userTagsInput.value = sujet.user_tags || '';

        updateToggleAppearance();

        noMoreSujetsDiv.classList.add('hidden');
        sujetContentDiv.classList.remove('hidden');
        saveButton.disabled = false;
        skipButton.disabled = false;
        deleteButton.disabled = false;
        updateGlobalButtonStates(true, history.length);
    }

    function getActiveFiltersForQuery() {
        if (editMode === 'filter') {
            return {
                tags: activeFilterState.tags,
                people: activeFilterState.people
            };
        } else { // 'tag' mode or any other mode
            return {
                tags: [],  // Send empty array to not filter by tags
                people: [] // Send empty array to not filter by people
            };
        }
    }

    async function updateSujetCount() {
        const filters = getActiveFiltersForQuery();
        let queryParams = [];
        if (filters.tags) queryParams.push(`tags=${encodeURIComponent(filters.tags)}`);
        if (filters.people) queryParams.push(`people=${encodeURIComponent(filters.people)}`);
        const queryString = queryParams.join('&');
        let filteredCount = 0;
        let totalCount = 0;

        try {
            const response = await fetch(`/get_sujets_count?${queryString}`);
            const data = await response.json();
            filteredCount = data.status === 'ok' ? data.count : 0;
        } catch (error) {
            console.error('Network error fetching filtered sujet count:', error);
        }

        try {
            const totalResponse = await fetch(`/get_sujets_count`);
            const totalData = await totalResponse.json();
            totalCount = totalData.status === 'ok' ? totalData.count : 0;
        } catch (error) {
            console.error('Network error fetching total sujet count:', error);
        }
        
        sujetCountDisplay.textContent = `${filteredCount} / ${totalCount}`;
    }

    async function loadNextSujet() {
        const filters = getActiveFiltersForQuery();
        let queryParams = [`offset=${currentOffset}`];
        if (filters.tags.length > 0) {
            queryParams.push(`tags=${filters.tags.map(encodeURIComponent).join(',')}`);
        }
        if (filters.people.length > 0) {
            queryParams.push(`people=${filters.people.map(encodeURIComponent).join(',')}`);
        }
        const queryString = queryParams.join('&');

        console.log(`--- DEBUG (loadNextSujet): Mode: ${editMode}, Query: /get_sujet?${queryString} ---`);

        try {
            const response = await fetch(`/get_sujet?${queryString}`);
            const data = await response.json();

            if (data.status === 'no_more_sujets') {
                sujetContentDiv.classList.add('hidden');
                noMoreSujetsDiv.classList.remove('hidden');
                const message = editMode === 'filter' ? 'No more sujets matching your filters.' : 'You have reached the end of the list.';
                noMoreSujetsDiv.textContent = message;
                saveButton.disabled = true;
                skipButton.disabled = true;
                deleteButton.disabled = true;
                currentSujetId = null;
                updateGlobalButtonStates(false, history.length);
            } else if (data.status === 'ok' && data.sujet) {
                if (history.length === 0 || history[history.length - 1] !== data.sujet.id) {
                    history.push(data.sujet.id);
                    if (history.length > historySize) history.shift();
                }
                displaySujet(data.sujet);
                currentOffset++;
            } else {
                handleLoadError("Error loading sujet: " + (data.message || "Unknown error"));
            }
        } catch (error) {
            handleLoadError("Network Error: " + error.message);
        }
    }
    
    function handleLoadError(message) {
        sujetContentDiv.classList.add('hidden');
        noMoreSujetsDiv.textContent = message;
        noMoreSujetsDiv.classList.remove('hidden');
        saveButton.disabled = true;
        skipButton.disabled = true;
        // backButton, quickSparkButton, and reverseSortButton remain conditionally enabled
        backButton.disabled = history.length <= 1;
        currentSujetId = null;
        // deleteButton is handled by updateGlobalButtonStates
        updateGlobalButtonStates(false, history.length);
    }

    async function loadSujetById(id) {
        if (id === null) return;
        try {
            const response = await fetch(`/get_sujet_by_id/${id}`);
            const data = await response.json();
            if (data.status === 'ok' && data.sujet) {
                displaySujet(data.sujet);
            } else {
                handleLoadError(`Error loading sujet ID ${id}: ` + (data.message || "Unknown error"));
            }
        } catch (error) {
            handleLoadError(`Network Error loading sujet ID ${id}: ` + error.message);
        }
    }

    async function loadEdgeSujet(edge) {
        const endpoint = edge === 'first' ? '/get_first_sujet' : '/get_last_sujet';
        console.log(`--- DEBUG (loadEdgeSujet): Fetching ${edge} sujet from ${endpoint} ---`);

        try {
            const response = await fetch(endpoint);
            const data = await response.json();

            if (data.status === 'no_more_sujets') {
                handleLoadError(`Could not load the ${edge} sujet. The database might be empty.`);
            } else if (data.status === 'ok' && data.sujet) {
                if (history.length === 0 || history[history.length - 1] !== data.sujet.id) {
                    history.push(data.sujet.id);
                    if (history.length > historySize) history.shift();
                }
                displaySujet(data.sujet);
            } else {
                handleLoadError(`Error loading ${edge} sujet: ` + (data.message || "Unknown error"));
            }
        } catch (error) {
            handleLoadError(`Network Error loading ${edge} sujet: ` + error.message);
        }
    }

    async function handleSujetAction(actionType) {
        if (!currentSujetData) return;
        let endpoint = '';
        let payload = { id: currentSujetData.id };
        const actionName = actionType === 'enriched' ? 'saving' : 'skipping'; // For better error messages

        if (actionType === 'enriched') {
            endpoint = '/save_sujet';
            payload.user_notes = userNotesTextarea.value.trim();
            payload.user_tags = userTagsInput.value.trim();
            payload.person = currentSujetData.person || '';
        } else if (actionType === 'skipped') {
            endpoint = '/skip_sujet';
        } else {
            return;
        }

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            // Accept 'ok', 'success', or 'partial_success' as valid for proceeding
            if (response.ok && (data.status === 'ok' || data.status === 'success' || data.status === 'partial_success')) {
                // If GSheet logging failed, we might want to inform the user but still proceed.
                if (data.status === 'partial_success') {
                    console.warn(`Action successful, but there was a server-side issue: ${data.message}`);
                }
                loadNextSujet();
                updateSujetCount();
            } else {
                alert(`Error ${actionName} sujet: ${data.message || 'Unknown error'}`);
            }
        } catch (error) {
            alert(`Network error when ${actionName} sujet. Check console.`);
        }
    }

    async function handleDeleteSujet() {
        console.log('[DEBUG] handleDeleteSujet called. currentSujetId:', currentSujetId);
        if (!currentSujetId) {
            console.log('[DEBUG] handleDeleteSujet: No currentSujetId, returning.');
            return;
        }

                console.log('[DEBUG] handleDeleteSujet: About to show window.confirm. Sujet:', currentSujetData.original_sujet);

    // --- Event Listeners --- 
    firstSujetButton.addEventListener('click', () => loadEdgeSujet('first'));
    lastSujetButton.addEventListener('click', () => loadEdgeSujet('last'));
        const userConfirmed = window.confirm(`Delete sujet: ${currentSujetData.original_sujet}?`); // Store result
        console.log('[DEBUG] handleDeleteSujet: window.confirm result:', userConfirmed); // Log the result

        if (!userConfirmed) { // Check the stored result
            console.log('[DEBUG] handleDeleteSujet: User cancelled delete (or confirm returned false).');
            return;
        }
        console.log('[DEBUG] handleDeleteSujet: User confirmed delete.');

        try {
            console.log('[DEBUG] handleDeleteSujet: About to fetch /delete_sujet/', currentSujetId);
            const response = await fetch(`/delete_sujet/${currentSujetId}`, { method: 'DELETE' });
            const data = await response.json();
            if (response.ok && data.status === 'success') {
                const indexInHistory = history.indexOf(currentSujetId);
                if (indexInHistory > -1) history.splice(indexInHistory, 1);
                loadNextSujet();
                updateSujetCount();
            } else {
                alert(`Error deleting sujet: ${data.message || 'Unknown error'}`);
            }
        } catch (error) {
            alert('Network error when deleting sujet. Check console.');
        }
    }

    async function handleQuickSpark() {
        try {
            const response = await fetch('/get_random_sujet');
            const data = await response.json();
            if (data.status === 'ok' && data.sujet) {
                if (history.length === 0 || history[history.length - 1] !== data.sujet.id) {
                    history.push(data.sujet.id);
                    if (history.length > historySize) history.shift();
                }
                displaySujet(data.sujet);
            } else {
                handleLoadError("Error getting a random sujet: " + (data.message || "Unknown error"));
            }
        } catch (error) {
            handleLoadError('Network error while fetching a random sujet: ' + error.message);
        }
    }

    async function handleReverseSort() {
        try {
            const response = await fetch('/toggle_sort', { method: 'POST' });
            const result = await response.json();
            if (response.ok && result.status === 'ok') {
                if (currentSujetId !== null) history.length = 0;
                currentOffset = 0;
                updateSujetCount();
                loadNextSujet();
            } else {
                alert(`Error toggling sort order: ${result.message || 'Unknown error'}`);
            }
        } catch (error) {
            alert('Network or unexpected error when toggling sort order. Check console.');
        }
    }

    // --- Event Listeners ---
    saveButton.addEventListener('click', () => handleSujetAction('enriched'));
    skipButton.addEventListener('click', () => handleSujetAction('skipped'));
    deleteButton.addEventListener('click', handleDeleteSujet);
    reverseSortButton.addEventListener('click', handleReverseSort);
    quickSparkButton.addEventListener('click', handleQuickSpark);

    backButton.addEventListener('click', () => {
        if (history.length > 1) {
            history.pop();
            const previousSujetId = history[history.length - 1];
            loadSujetById(previousSujetId);
        } else {
            backButton.disabled = true;
        }
    });

    modeToggleRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            editMode = e.target.value;
            updateToggleAppearance(); // Ensure toggles reflect the new mode
        });
    });

    // --- Initial Load ---
    function initializeApp() {
        renderToggles(tagTogglesDiv, predefinedTags, 'tag');
        renderToggles(personTogglesDiv, predefinedPeople, 'person');

        // Set initial filter state
        activeFilterState.tags = predefinedTags.map(t => t.toLowerCase()); // Default to ALL tags
        activeFilterState.people = predefinedPeople.map(p => p.toLowerCase()); // Default to all people

        updateToggleAppearance();
        updateSujetCount();
        loadNextSujet();
    }

    initializeApp();

    // Event handlers for selectAll buttons are now defined inline within renderToggles.
});