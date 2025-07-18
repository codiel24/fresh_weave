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
    const quickSparkButton = document.getElementById('quick-spark-button');
    const favoriteButton = document.getElementById('favorite-button');
    const firstSujetButton = document.getElementById('first-sujet-button');
    const lastSujetButton = document.getElementById('last-sujet-button');
    const editTitleButton = document.getElementById('edit-title-button');
    const editTitleContainer = document.getElementById('edit-title-container');
    const editTitleInput = document.getElementById('edit-title-input');
    const saveTitleButton = document.getElementById('save-title-button');
    const cancelTitleButton = document.getElementById('cancel-title-button');

    const sujetContentDiv = document.getElementById('sujet-content');
    const noMoreSujetsDiv = document.getElementById('no-more-sujets');

    // --- DOM Elements for New Sujet Modal ---
    const newSujetButton = document.getElementById('new-sujet-button');
    const newSujetModal = document.getElementById('new-sujet-modal');
    const closeModalButton = document.getElementById('close-modal');
    const newSujetTitleInput = document.getElementById('new-sujet-title');
    const createSujetButton = document.getElementById('create-sujet-button');
    const cancelSujetButton = document.getElementById('cancel-sujet-button');

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

        let ideaButton = null;

        items.forEach((item, index) => {
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

            // Remember the "Idea/Project" button for tag type
            if (type === 'tag' && item.trim().toLowerCase() === 'idea/project') {
                ideaButton = button;
            }
        });

        // For tags, add favorite button and Select All button after "Idea/Project"
        if (type === 'tag' && ideaButton) {
            // Move existing favorite button to tag area
            const existingFavBtn = document.getElementById('favorite-button');
            if (existingFavBtn) {
                existingFavBtn.className = 'tag-toggle'; // Make it look like other tag buttons
                ideaButton.insertAdjacentElement('afterend', existingFavBtn);
            }

            const selectAllBtn = document.createElement('button');
            selectAllBtn.className = 'select-all-button';
            selectAllBtn.textContent = 'All';
            selectAllBtn.id = 'select-all-tags';
            selectAllBtn.onclick = () => {
                const allBtns = container.querySelectorAll('.tag-toggle');
                const anyInactive = Array.from(allBtns).some(btn => !btn.classList.contains('active'));
                allBtns.forEach(btn => btn.classList.toggle('active', anyInactive));
                if (editMode === 'filter') updateActiveFilterStateFromUI();
                else updateSujetDataFromToggles();
            };
            // Insert the All button after the favorite button
            if (existingFavBtn) {
                existingFavBtn.insertAdjacentElement('afterend', selectAllBtn);
            } else {
                ideaButton.insertAdjacentElement('afterend', selectAllBtn);
            }
        }

        // For people, add Select All button at the end (as before)
        if (type === 'person') {
            const selectAllBtn = document.createElement('button');
            selectAllBtn.className = 'select-all-button';
            selectAllBtn.textContent = 'All';
            selectAllBtn.id = 'select-all-people';
            selectAllBtn.onclick = () => {
                const allBtns = container.querySelectorAll('.person-toggle');
                const anyInactive = Array.from(allBtns).some(btn => !btn.classList.contains('active'));
                allBtns.forEach(btn => btn.classList.toggle('active', anyInactive));
                if (editMode === 'filter') updateActiveFilterStateFromUI();
                else updateSujetDataFromToggles();
            };
            container.appendChild(selectAllBtn);
        }
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
            let sujetPeople = parseCsvString(currentSujetData.person);
            // Default to all people if none assigned in tag mode
            if (sujetPeople.length === 0) sujetPeople = predefinedPeople.map(p => p.toLowerCase());
            document.querySelectorAll('.tag-toggle').forEach(btn => {
                btn.classList.toggle('active', sujetTags.includes(btn.dataset.value));
            });
            document.querySelectorAll('.person-toggle').forEach(btn => {
                btn.classList.toggle('active', sujetPeople.includes(btn.dataset.value));
            });
        }
    }

    function updateFavoriteButtonState() {
        if (!currentSujetData) return;

        const sujetTags = parseCsvString(userTagsInput.value);
        const isFavorite = sujetTags.includes('fav');

        // Update button appearance
        if (isFavorite) {
            favoriteButton.textContent = '★'; // Filled star
            favoriteButton.classList.add('favorite-active');
        } else {
            favoriteButton.textContent = '☆'; // Empty star
            favoriteButton.classList.remove('favorite-active');
        }
    }

    function toggleFavorite() {
        if (!currentSujetData) return;

        const sujetTags = parseCsvString(userTagsInput.value);
        const favIndex = sujetTags.indexOf('fav');

        if (favIndex !== -1) {
            // Remove 'fav' tag
            sujetTags.splice(favIndex, 1);
        } else {
            // Add 'fav' tag
            sujetTags.push('fav');
        }

        // Update the tags input field
        userTagsInput.value = sujetTags.join(', ');

        // Update button appearance
        updateFavoriteButtonState();

        // Update tag toggles if in tag mode
        if (editMode === 'tag') {
            updateToggleAppearance();
        }
    }

    function displaySujet(sujet) {
        currentSujetId = sujet.id;
        currentSujetData = sujet;
        // Parse ID and Title from sujet.original_sujet (e.g., "ID: 123 - Title Text")
        const match = sujet.original_sujet.match(/^ID:\s*(\d+)\s*-\s*(.*)$/);
        let titleText;
        if (match && match[1] && match[2]) {
            displaySujetIdSpan.textContent = match[1]; // Just the ID number
            titleText = match[2]; // Just the Title text
            originalSujetSpan.textContent = titleText;
        } else {
            // Fallback if parsing fails, though this shouldn't happen with consistent data
            displaySujetIdSpan.textContent = sujet.id; // Use sujet.id as a fallback for the number
            titleText = sujet.original_sujet; // Show the original string as fallback title
            originalSujetSpan.textContent = titleText;
        }

        // Set title attribute for tooltip if text is longer than what fits in 2 lines
        if (titleText.length > 80) { // Approximate character limit for 2 lines
            originalSujetSpan.setAttribute('title', titleText);
        } else {
            originalSujetSpan.removeAttribute('title');
        }

        aiSuggestionSpan.textContent = sujet.ai_suggestion;
        userNotesTextarea.value = sujet.user_notes || '';
        userTagsInput.value = sujet.user_tags || '';

        // Display date_created if available
        const dateCreatedSpan = document.getElementById('date-created');
        if (dateCreatedSpan) {
            if (sujet.date_created) {
                // Convert from YYYY-MM-DD to yy.mm.dd format
                const dateParts = sujet.date_created.split('-');
                if (dateParts.length === 3) {
                    const year = dateParts[0].substring(2); // Get last 2 digits of year
                    const month = dateParts[1];
                    const day = dateParts[2];
                    dateCreatedSpan.textContent = `${day}.${month}.${year}`;
                } else {
                    dateCreatedSpan.textContent = sujet.date_created;
                }
            } else {
                dateCreatedSpan.textContent = 'N/A';
            }
        }

        updateToggleAppearance();
        updateFavoriteButtonState();

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
        if (filters.tags && filters.tags.length > 0) {
            queryParams.push(`tags=${filters.tags.map(encodeURIComponent).join(',')}`);
        }
        if (filters.people && filters.people.length > 0) {
            queryParams.push(`people=${filters.people.map(encodeURIComponent).join(',')}`);
        }
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
        // Get the active filters
        const filters = getActiveFiltersForQuery();

        // Build the query string for the request
        const queryParams = [`offset=${currentOffset}`];
        if (filters.tags.length) queryParams.push(`tags=${filters.tags.map(encodeURIComponent).join(',')}`);
        if (filters.people.length) queryParams.push(`people=${filters.people.map(encodeURIComponent).join(',')}`);

        try {
            const response = await fetch(`/get_sujet?${queryParams.join('&')}`);
            const data = await response.json();

            if (data.status === 'ok' && data.sujet) {
                // Always add the sujet to history, even if it's the first one
                history.push(data.sujet.id);
                if (history.length > historySize) history.shift();

                currentSujetData = data.sujet;
                currentSujetId = data.sujet.id;
                displaySujet(data.sujet);

                // Update back button state
                backButton.disabled = history.length <= 1;

                // Increment offset for next fetch
                currentOffset++;
            } else if (data.status === 'no_more_sujets') {
                handleLoadError('No more sujets match your current filters.');
            } else {
                handleLoadError(`Error loading sujet: ${data.message || 'Unknown error'}`);
            }
        } catch (error) {
            handleLoadError(`Network error: ${error.message}`);
        }
    }

    function handleLoadError(message) {
        sujetContentDiv.classList.add('hidden');
        noMoreSujetsDiv.textContent = message;
        noMoreSujetsDiv.classList.remove('hidden');
        saveButton.disabled = true;
        skipButton.disabled = true;
        // backButton, quickSparkButton, and sortOrderButton remain conditionally enabled
        backButton.disabled = history.length <= 1;
        currentSujetId = null;
        // deleteButton is handled by updateGlobalButtonStates
        updateGlobalButtonStates(false, history.length);
    }

    async function loadSujetById(id) {
        if (!id) return;
        console.log(`--- DEBUG (loadSujetById): Loading sujet by ID: ${id} ---`);
        try {
            const response = await fetch(`/get_sujet_by_id/${id}`);
            const data = await response.json();
            if (data.status === 'ok' && data.sujet) {
                // When going 'back', the history is managed by the backButton listener.
                // We do NOT push to history here, as it would create duplicates.
                displaySujet(data.sujet);
            } else {
                handleLoadError(`Could not load sujet with ID ${id}. It may have been deleted.`);
            }
        } catch (error) {
            handleLoadError(`Network error loading sujet ID ${id}: ${error.message}`);
        }
    }

    async function loadAdjacentSujet(direction = 'next') {
        if (!currentSujetId) {
            console.warn('loadAdjacentSujet called but currentSujetId is null');
            return;
        }

        // Throttle rapid consecutive calls, but allow fast forward during long press
        const now = Date.now();
        const isInLongPress = skipIsLongPressing || backIsLongPressing;
        const throttleTime = isInLongPress ? 50 : NAVIGATION_THROTTLE_MS; // Shorter throttle during long press

        if (now - lastNavigationTime < throttleTime) {
            console.log(`[THROTTLE] Navigation call ignored, too soon (${now - lastNavigationTime}ms ago, threshold: ${throttleTime}ms)`);
            return;
        }
        lastNavigationTime = now;

        debugNavigation(`LOAD ADJACENT START (${direction})`, currentSujetId, false);
        console.trace(`[TRACE] loadAdjacentSujet called with direction: ${direction}`);

        const filters = getActiveFiltersForQuery();
        const qp = [
            `id=${currentSujetId}`,
            `direction=${direction}`
        ];
        if (filters.tags.length) qp.push(`tags=${filters.tags.map(encodeURIComponent).join(',')}`);
        if (filters.people.length) qp.push(`people=${filters.people.map(encodeURIComponent).join(',')}`);

        try {
            const res = await fetch(`/adjacent_sujet?${qp.join('&')}`);
            const data = await res.json();

            if (data.status === 'ok' && data.sujet) {
                // Add to history if this is a new sujet
                if (history.length === 0 || history[history.length - 1] !== data.sujet.id) {
                    history.push(data.sujet.id);
                    if (history.length > historySize) history.shift();
                } else if (history.length === 0) {
                    history.push(data.sujet.id);
                }

                displaySujet(data.sujet);
                debugNavigation(`LOAD ADJACENT SUCCESS (${direction})`, data.sujet.id, false);

                // Clean up any stuck long press states after successful navigation
                cleanupAllLongPressStates();

                // Update back button state
                backButton.disabled = history.length <= 1;
            } else if (data.status === 'no_more_sujets') {
                // Wrap around to first or last depending on direction
                const edge = direction === 'next' ? 'first' : 'last';
                await loadEdgeSujet(edge);
            } else {
                handleLoadError(`Navigation error: ${data.message || 'unknown'}`);
            }
        } catch (err) {
            handleLoadError('Network error navigating: ' + err.message);
        }
    }

    async function loadEdgeSujet(edge) {
        try {
            // Build query string with filters if in filter mode
            let url = `/${edge}`;

            // If in filter mode, include the active filters
            if (editMode === 'filter') {
                const filters = getActiveFiltersForQuery();
                const queryParams = [];

                if (filters.tags.length) {
                    queryParams.push(`tags=${filters.tags.map(encodeURIComponent).join(',')}`);
                }

                if (filters.people.length) {
                    queryParams.push(`people=${filters.people.map(encodeURIComponent).join(',')}`);
                }

                if (queryParams.length > 0) {
                    url += `?${queryParams.join('&')}`;
                }
            }

            const response = await fetch(url);
            const data = await response.json();
            if (data.status === 'ok' && data.sujet) {
                if (history.length === 0 || history[history.length - 1] !== data.sujet.id) {
                    history.push(data.sujet.id);
                    if (history.length > historySize) history.shift();
                }
                displaySujet(data.sujet);
            } else {
                handleLoadError(`Error loading ${edge} sujet: ${data.message || 'Unknown error'}`);
            }
        } catch (error) {
            handleLoadError(`Network error loading ${edge} sujet: ${error.message}`);
        }
    }

    // --- Action Handlers (Save, Skip, Delete, etc.) ---

    function getSelectedPeopleFromToggles() {
        return Array.from(personTogglesDiv.querySelectorAll('.person-toggle.active')).map(btn => {
            return btn.title || btn.textContent.trim();
        });
    }

    async function handleSujetAction(actionType) {
        if (!currentSujetData) return;

        let endpoint = '';
        let payload = { id: currentSujetData.id };

        if (actionType === 'save') {
            endpoint = '/save_sujet';
            payload.user_notes = userNotesTextarea.value;
            payload.user_tags = userTagsInput.value;
            payload.person = getSelectedPeopleFromToggles().join(',');
        } else if (actionType === 'skipped') {
            endpoint = '/skip_sujet';
        } else {
            return; // Should not happen for this function
        }

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error(`Server responded with status ${response.status}`);
            }

            await response.json();
            loadAdjacentSujet('next');
        } catch (error) {
            console.error(`--- ERROR (handleSujetAction): Action ${actionType} failed:`, error);
            alert(`Action failed: ${error.message}. Please try again.`);
        }
    }

    async function handleDeleteSujet() {
        console.log('[DEBUG] handleDeleteSujet called. currentSujetId:', currentSujetId);
        if (!currentSujetId) {
            console.log('[DEBUG] handleDeleteSujet: No currentSujetId, returning.');
            return;
        }

        console.log('[DEBUG] handleDeleteSujet: Proceeding with deletion for sujet:', currentSujetData.original_sujet);

        // Show confirmation dialog before proceeding with deletion
        if (!confirm("Are you sure you want to delete this sujet? This action cannot be undone.")) {
            console.log('[DEBUG] handleDeleteSujet: Deletion cancelled by user.');
            return; // Exit if user cancels
        }

        try {
            console.log('[DEBUG] handleDeleteSujet: About to fetch /delete_sujet/', currentSujetId);
            const response = await fetch(`/delete_sujet/${currentSujetId}`, { method: 'DELETE' });

            // Check if response is ok before trying to parse JSON
            if (!response.ok) {
                throw new Error(`Server responded with status ${response.status}`);
            }

            const data = await response.json();
            console.log('[DEBUG] handleDeleteSujet: Response received:', data);

            // After deletion, move to the next sujet
            loadAdjacentSujet('next');
            updateSujetCount();
        } catch (error) {
            console.error('Network error when deleting sujet:', error);
            alert(`Failed to delete sujet: ${error.message}. Please try again.`);
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

    async function loadEdgeSujet(edge) {
        try {
            const response = await fetch(`/${edge}`);
            const data = await response.json();
            if (data.status === 'ok' && data.sujet) {
                // Add to history if this is a new sujet
                if (history.length === 0 || history[history.length - 1] !== data.sujet.id) {
                    history.push(data.sujet.id);
                    if (history.length > historySize) history.shift();
                }

                currentSujetData = data.sujet;
                currentSujetId = data.sujet.id;
                displaySujet(data.sujet);

                // Update back button state
                backButton.disabled = history.length <= 1;
            } else {
                handleLoadError(`Error loading ${edge} sujet: ${data.message || 'Unknown error'}`);
            }
        } catch (error) {
            handleLoadError(`Network error loading ${edge} sujet: ${error.message}`);
        }
    }

    function showTitleEditForm() {
        if (!currentSujetData) return;
        const titleText = originalSujetSpan.textContent.trim();
        editTitleInput.value = titleText;
        originalSujetSpan.style.display = 'none';
        editTitleContainer.classList.remove('hidden');
        editTitleInput.focus();
    }

    function hideTitleEditForm() {
        originalSujetSpan.style.display = 'inline';
        editTitleContainer.classList.add('hidden');
    }

    function saveEditedTitle() {
        if (!currentSujetData || !currentSujetId) return;
        const newTitle = editTitleInput.value.trim();
        if (!newTitle) {
            alert('Title cannot be empty');
            return;
        }
        fetch(`/update_title/${currentSujetId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle })
        })
            .then(response => {
                if (!response.ok) throw new Error('Failed to update title');
                return response.json();
            })
            .then(data => {
                originalSujetSpan.textContent = newTitle;
                hideTitleEditForm();
                if (currentSujetData) {
                    const idPrefix = currentSujetData.original_sujet.match(/^ID:\s*(\d+)\s*-\s*/);
                    if (idPrefix && idPrefix[0]) {
                        currentSujetData.original_sujet = idPrefix[0] + newTitle;
                    } else {
                        currentSujetData.original_sujet = `ID: ${currentSujetId} - ${newTitle}`;
                    }
                }
            })
            .catch(error => {
                console.error('Error updating title:', error);
                alert('Failed to update title. Please try again.');
            });
    }

    function openNewSujetModal() {
        newSujetTitleInput.value = '';
        newSujetModal.classList.remove('hidden');
        newSujetTitleInput.focus();
    }

    function closeNewSujetModal() {
        newSujetModal.classList.add('hidden');
    }

    async function createNewSujet() {
        const title = newSujetTitleInput.value.trim();
        if (!title) {
            alert('Title cannot be empty');
            return;
        }
        try {
            const response = await fetch('/add_sujet', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: title })
            });
            const result = await response.json();
            if (result.status === 'success') {
                closeNewSujetModal();
                if (result.sujet && result.sujet.id) {
                    currentSujetData = result.sujet;
                    currentSujetId = result.sujet.id;
                    displaySujet(result.sujet);
                }
            } else {
                console.error('Error creating sujet:', result.message || 'Unknown error');
            }
        } catch (error) {
            console.error('Error creating sujet:', error);
        }
    }    // --- Fast Forward Long Press Implementation ---
    let skipLongPressTimer = null;
    let skipFastForwardInterval = null;
    let skipIsLongPressing = false;
    let skipWasLongPress = false;

    let backLongPressTimer = null;
    let backFastForwardInterval = null;
    let backIsLongPressing = false;
    let backWasLongPress = false;

    // Global cleanup function to reset all long press states
    function cleanupAllLongPressStates() {
        // Skip button cleanup
        if (skipLongPressTimer) {
            clearTimeout(skipLongPressTimer);
            skipLongPressTimer = null;
        }
        if (skipFastForwardInterval) {
            clearInterval(skipFastForwardInterval);
            skipFastForwardInterval = null;
        }
        skipIsLongPressing = false;
        skipWasLongPress = false;

        // Back button cleanup
        if (backLongPressTimer) {
            clearTimeout(backLongPressTimer);
            backLongPressTimer = null;
        }
        if (backFastForwardInterval) {
            clearInterval(backFastForwardInterval);
            backFastForwardInterval = null;
        }
        backIsLongPressing = false;
        backWasLongPress = false;
    }

    function startSkipFastForward() {
        if (skipIsLongPressing) return; // Prevent multiple intervals
        skipIsLongPressing = true;

        // Fast forward every 100ms during long press (10 times per second)
        skipFastForwardInterval = setInterval(() => {
            if (!skipButton.disabled && skipIsLongPressing) {
                debugNavigation('SKIP FAST FORWARD', currentSujetId, true);
                // Fast forward just navigates, doesn't save
                loadAdjacentSujet('next');
            } else {
                stopSkipFastForward();
            }
        }, 100);
    }

    function stopSkipFastForward() {
        if (skipFastForwardInterval) {
            clearInterval(skipFastForwardInterval);
            skipFastForwardInterval = null;
        }
        skipIsLongPressing = false;
    }

    function startBackFastForward() {
        if (backIsLongPressing) return; // Prevent multiple intervals
        backIsLongPressing = true;

        // Fast backward every 100ms during long press (10 times per second) 
        backFastForwardInterval = setInterval(() => {
            if (!backButton.disabled && backIsLongPressing) {
                debugNavigation('BACK FAST FORWARD', currentSujetId, true);
                loadAdjacentSujet('prev');
            } else {
                stopBackFastForward();
            }
        }, 100);
    }

    function stopBackFastForward() {
        if (backFastForwardInterval) {
            clearInterval(backFastForwardInterval);
            backFastForwardInterval = null;
        }
        backIsLongPressing = false;
    }

    // === MOBILE-FIRST APPROACH ===
    // Primary: Touch events for mobile (Chrome Android)
    // Fallback: Click events for desktop testing

    // Touch events for mobile - skip button
    skipButton.addEventListener('touchstart', (e) => {
        if (!skipButton.disabled) {
            e.preventDefault(); // Prevent mouse events and click
            skipWasLongPress = false;
            skipLongPressTimer = setTimeout(() => {
                skipWasLongPress = true;
                startSkipFastForward();
            }, 300);
        }
    });

    skipButton.addEventListener('touchend', (e) => {
        e.preventDefault(); // Prevent mouse events and click
        clearTimeout(skipLongPressTimer);
        stopSkipFastForward();

        // If it wasn't a long press, trigger normal skip after a short delay
        if (!skipWasLongPress) {
            setTimeout(() => {
                loadAdjacentSujet('next');
            }, 50);
        }

        // Reset the flag after a delay
        setTimeout(() => {
            skipWasLongPress = false;
        }, 150);
    });

    skipButton.addEventListener('touchcancel', (e) => {
        e.preventDefault();
        clearTimeout(skipLongPressTimer);
        stopSkipFastForward();
        skipWasLongPress = false;
    });

    // Touch events for mobile - back button
    backButton.addEventListener('touchstart', (e) => {
        if (!backButton.disabled) {
            e.preventDefault(); // Prevent mouse events and click
            backWasLongPress = false;
            backLongPressTimer = setTimeout(() => {
                backWasLongPress = true;
                startBackFastForward();
            }, 300);
        }
    });

    backButton.addEventListener('touchend', (e) => {
        e.preventDefault(); // Prevent mouse events and click
        clearTimeout(backLongPressTimer);
        stopBackFastForward();

        // If it wasn't a long press, trigger normal back after a short delay
        if (!backWasLongPress) {
            setTimeout(() => {
                loadAdjacentSujet('prev');
            }, 50);
        }

        // Reset the flag after a delay
        setTimeout(() => {
            backWasLongPress = false;
        }, 150);
    });

    backButton.addEventListener('touchcancel', (e) => {
        e.preventDefault();
        clearTimeout(backLongPressTimer);
        stopBackFastForward();
        backWasLongPress = false;
    });

    // Debug function to track navigation
    function debugNavigation(action, sujetId, wasLongPress) {
        console.log(`[NAV DEBUG] ${action} - SujetID: ${sujetId}, LongPress: ${wasLongPress}, CurrentOffset: ${currentOffset}`);
    }

    // --- Event Listeners ---
    saveButton.addEventListener('click', () => handleSujetAction('save'));
    
    // Skip and Back buttons: Touch events only (Chrome Android app)
    // No click events needed - touch handles everything
    
    deleteButton.addEventListener('click', handleDeleteSujet);
    quickSparkButton.addEventListener('click', handleQuickSpark);
    favoriteButton.addEventListener('click', toggleFavorite);
    editTitleButton.addEventListener('click', showTitleEditForm);
    saveTitleButton.addEventListener('click', saveEditedTitle);
    cancelTitleButton.addEventListener('click', hideTitleEditForm);
    firstSujetButton.addEventListener('click', () => loadEdgeSujet('first'));
    lastSujetButton.addEventListener('click', () => loadEdgeSujet('last'));

    // Back button: Touch events only (Chrome Android app)
    // No click event needed - touch handles everything

    // Title expansion click handler
    originalSujetSpan.addEventListener('click', () => {
        originalSujetSpan.classList.toggle('expanded');
    });

    // Click outside to collapse expanded title
    document.addEventListener('click', (event) => {
        if (!originalSujetSpan.contains(event.target) && originalSujetSpan.classList.contains('expanded')) {
            originalSujetSpan.classList.remove('expanded');
        }
    });

    // New Sujet Modal Event Listeners
    newSujetButton.addEventListener('click', openNewSujetModal);
    closeModalButton.addEventListener('click', closeNewSujetModal);
    cancelSujetButton.addEventListener('click', closeNewSujetModal);
    createSujetButton.addEventListener('click', createNewSujet);

    // Close modal if clicking outside of it
    window.addEventListener('click', (event) => {
        if (event.target === newSujetModal) {
            closeNewSujetModal();
        }
    });

    // Allow pressing Enter in the title input to submit
    newSujetTitleInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            createNewSujet();
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
        // Start at the last (newest) sujet for intuitive ascending navigation
        loadEdgeSujet('last');
    }

    initializeApp();

    // Track how many times event listeners are attached
    let eventListenerCount = 0;

    // Navigation throttling to prevent rapid consecutive calls
    let lastNavigationTime = 0;
    const NAVIGATION_THROTTLE_MS = 200;
});