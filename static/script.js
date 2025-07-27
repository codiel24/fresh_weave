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
    // const aiSuggestionSpan = document.getElementById('ai-suggestion'); // AI suggestions discontinued
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
    const titleInput = document.getElementById('title-input');
    const saveTitleButton = document.getElementById('save-title-button');
    const cancelTitleButton = document.getElementById('cancel-title-button');

    const sujetContentDiv = document.getElementById('sujet-content');
    const noMoreSujetsDiv = document.getElementById('no-more-sujets');

    // --- DOM Elements for New Sujet ---
    const newSujetButton = document.getElementById('new-sujet-button');

    // --- DOM Elements for Search ---
    const searchButton = document.getElementById('search-button');
    const searchContainer = document.getElementById('search-container');
    const searchInput = document.getElementById('search-input');
    const searchApplyButton = document.getElementById('search-apply-button');
    const searchClearButton = document.getElementById('search-clear-button');

    // --- State Variables ---
    let currentSujetId = null;
    let currentSujetData = null;
    let currentOffset = 0;
    const history = [];
    const historySize = 10;
    let editMode = 'filter'; // 'filter' or 'tag'
    let titleEditMode = null; // 'edit' or 'new' - tracks what we're doing with the title input
    let activeFilterState = { tags: [], people: [], search: '' };

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
                console.log('[SELECT ALL DEBUG] Tags Select All clicked, mode:', editMode);
                const allBtns = container.querySelectorAll('.tag-toggle');
                const anyInactive = Array.from(allBtns).some(btn => !btn.classList.contains('active'));
                console.log('[SELECT ALL DEBUG] anyInactive:', anyInactive, 'will', anyInactive ? 'activate' : 'deactivate', 'all tags');

                allBtns.forEach(btn => btn.classList.toggle('active', anyInactive));

                if (editMode === 'filter') {
                    updateActiveFilterStateFromUI();
                    updateSujetCount();
                    console.log('[SELECT ALL DEBUG] Filter state updated:', activeFilterState.tags);
                } else {
                    updateSujetDataFromToggles();
                }
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
                console.log('[SELECT ALL DEBUG] People Select All clicked, mode:', editMode);
                const allBtns = container.querySelectorAll('.person-toggle');
                const anyInactive = Array.from(allBtns).some(btn => !btn.classList.contains('active'));
                console.log('[SELECT ALL DEBUG] anyInactive:', anyInactive, 'will', anyInactive ? 'activate' : 'deactivate', 'all people');

                allBtns.forEach(btn => btn.classList.toggle('active', anyInactive));

                if (editMode === 'filter') {
                    updateActiveFilterStateFromUI();
                    updateSujetCount();
                    console.log('[SELECT ALL DEBUG] Filter state updated:', activeFilterState.people);
                } else {
                    updateSujetDataFromToggles();
                }
            };
            container.appendChild(selectAllBtn);
        }
    }

    function handleToggleClick(event) {
        const button = event.target;
        const value = button.dataset.value;

        console.log('[TOGGLE] Clicked:', value, 'mode:', editMode, 'was active:', button.classList.contains('active'));

        // SIMPLE RULE: Toggle button state immediately and permanently
        button.classList.toggle('active');
        const isNowActive = button.classList.contains('active');

        console.log('[TOGGLE] Now active:', isNowActive);

        if (editMode === 'filter') {
            // In filter mode: update internal state to match UI, update count
            updateActiveFilterStateFromUI();
            updateSujetCount();
            console.log('[TOGGLE] Filter state updated:', activeFilterState);
        } else {
            // In tag mode: update the current sujet's data from toggles
            console.log('[TOGGLE] Tag mode - updating current sujet data');
            if (!currentSujetData) {
                console.log('[TOGGLE] ERROR: No currentSujetData available');
                return;
            }
            updateSujetDataFromToggles();
            console.log('[TOGGLE] Updated sujet data from toggles');
        }
    } function updateActiveFilterStateFromUI() {
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

    function updateToggleAppearance(reason = 'unknown') {
        console.log('[TOGGLE APPEARANCE] Called for reason:', reason, 'mode:', editMode);

        // CRITICAL: Only update appearance when loading new data, not during user interaction
        if (reason !== 'new-sujet' && reason !== 'mode-change' && reason !== 'init') {
            console.log('[TOGGLE APPEARANCE] Skipping - not a data load event');
            return;
        }

        if (editMode === 'filter') {
            console.log('[TOGGLE APPEARANCE] Updating filter mode buttons based on activeFilterState:', activeFilterState);
            document.querySelectorAll('.tag-toggle').forEach(btn => {
                const shouldBeActive = activeFilterState.tags.includes(btn.dataset.value);
                btn.classList.toggle('active', shouldBeActive);
            });
            document.querySelectorAll('.person-toggle').forEach(btn => {
                const shouldBeActive = activeFilterState.people.includes(btn.dataset.value);
                btn.classList.toggle('active', shouldBeActive);
            });
        } else { // 'tag' mode
            if (!currentSujetData) {
                console.log('[TOGGLE APPEARANCE] No currentSujetData in tag mode, skipping');
                return;
            }
            console.log('[TOGGLE APPEARANCE] Updating tag mode buttons based on current sujet');
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

        // Don't call updateToggleAppearance() - let user manual toggles remain as they are
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

        // aiSuggestionSpan.textContent = sujet.ai_suggestion; // AI suggestions discontinued
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

        updateToggleAppearance('new-sujet');
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
                people: activeFilterState.people,
                search: activeFilterState.search
            };
        } else { // 'tag' mode or any other mode
            return {
                tags: [],  // Send empty array to not filter by tags
                people: [], // Send empty array to not filter by people
                search: activeFilterState.search // Keep search in tag mode too
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
        if (filters.search && filters.search.trim()) {
            queryParams.push(`search=${encodeURIComponent(filters.search)}`);
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

        // In filter mode, show only the filtered count; in tag mode, show filtered/total
        if (editMode === 'filter') {
            sujetCountDisplay.textContent = `${filteredCount}`;
        } else {
            sujetCountDisplay.textContent = `${filteredCount} / ${totalCount}`;
        }
    }

    async function loadNextSujet() {
        console.log('[NAV DEBUG] loadNextSujet called with offset:', currentOffset, 'mode:', editMode);

        // Get the active filters
        const filters = getActiveFiltersForQuery();
        console.log('[NAV DEBUG] Active filters:', filters);

        // Build the query string for the request
        const queryParams = [`offset=${currentOffset}`];
        if (filters.tags.length) queryParams.push(`tags=${filters.tags.map(encodeURIComponent).join(',')}`);
        if (filters.people.length) queryParams.push(`people=${filters.people.map(encodeURIComponent).join(',')}`);
        if (filters.search && filters.search.trim()) queryParams.push(`search=${encodeURIComponent(filters.search)}`);

        console.log('[NAV DEBUG] Query params:', queryParams.join('&'));

        try {
            const response = await fetch(`/get_sujet?${queryParams.join('&')}`);
            const data = await response.json();

            console.log('[NAV DEBUG] Response data:', {
                status: data.status,
                sujetId: data.sujet?.id,
                currentOffset: currentOffset
            });

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

        // Throttle rapid consecutive calls
        const now = Date.now();
        if (now - lastNavigationTime < NAVIGATION_THROTTLE_MS) {
            console.log(`[THROTTLE] Navigation call ignored, too soon (${now - lastNavigationTime}ms ago)`);
            return;
        }
        lastNavigationTime = now;

        debugNavigation(`LOAD ADJACENT START (${direction})`, currentSujetId);
        console.trace(`[TRACE] loadAdjacentSujet called with direction: ${direction}`);

        const filters = getActiveFiltersForQuery();
        const qp = [
            `id=${currentSujetId}`,
            `direction=${direction}`
        ];
        if (filters.tags.length) qp.push(`tags=${filters.tags.map(encodeURIComponent).join(',')}`);
        if (filters.people.length) qp.push(`people=${filters.people.map(encodeURIComponent).join(',')}`);
        if (filters.search && filters.search.trim()) qp.push(`search=${encodeURIComponent(filters.search)}`);

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
                debugNavigation(`LOAD ADJACENT SUCCESS (${direction})`, data.sujet.id);

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

                if (filters.search && filters.search.trim()) {
                    queryParams.push(`search=${encodeURIComponent(filters.search)}`);
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

            // Only navigate after save actions, not delete (delete handles its own navigation)
            if (actionType !== 'delete') {
                loadAdjacentSujet('next');
            }
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
            console.log('[DELETE DEBUG] About to call loadAdjacentSujet(next) from deleted sujet:', currentSujetId);
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

    function showTitleInput(mode, currentTitle = '') {
        console.log(`[TITLE INPUT] showTitleInput called - mode: ${mode}`);

        titleEditMode = mode;
        titleInput.value = currentTitle;

        // Hide original title and edit button (if editing existing)
        if (mode === 'edit') {
            originalSujetSpan.style.display = 'none';
            editTitleButton.style.display = 'none';
        }

        // Show input and save/cancel buttons
        titleInput.style.display = 'inline';
        saveTitleButton.style.display = 'inline';
        cancelTitleButton.style.display = 'inline';

        // Focus the input field
        titleInput.focus();
        if (currentTitle) {
            titleInput.select(); // Select all text for easy editing
        }
    }

    function hideTitleInput() {
        console.log(`[TITLE INPUT] hideTitleInput called - was mode: ${titleEditMode}`);

        // Show original title and edit button if we were editing
        if (titleEditMode === 'edit') {
            originalSujetSpan.style.display = 'inline';
            editTitleButton.style.display = 'inline';
        }

        // Hide input and save/cancel buttons
        titleInput.style.display = 'none';
        saveTitleButton.style.display = 'none';
        cancelTitleButton.style.display = 'none';

        titleEditMode = null;
    }

    // Wrapper functions for specific use cases
    function startEditingTitle() {
        if (!currentSujetData) return;
        const titleText = originalSujetSpan.textContent.trim();
        showTitleInput('edit', titleText);
    }

    function startCreatingNewSujet() {
        showTitleInput('new', '');
    }

    async function saveTitleAction() {
        const title = titleInput.value.trim();
        if (!title) {
            alert('Title cannot be empty');
            return;
        }

        try {
            if (titleEditMode === 'edit') {
                // Update existing sujet title
                if (!currentSujetData || !currentSujetId) return;

                const response = await fetch(`/update_title/${currentSujetId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: title })
                });

                if (!response.ok) throw new Error('Failed to update title');
                const data = await response.json();

                // Update the display
                originalSujetSpan.textContent = title;
                if (currentSujetData) {
                    const idPrefix = currentSujetData.original_sujet.match(/^ID:\s*(\d+)\s*-\s*/);
                    if (idPrefix && idPrefix[0]) {
                        currentSujetData.original_sujet = idPrefix[0] + title;
                    } else {
                        currentSujetData.original_sujet = `ID: ${currentSujetId} - ${title}`;
                    }
                }

            } else if (titleEditMode === 'new') {
                // Create new sujet
                const response = await fetch('/add_sujet', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: title })
                });

                const result = await response.json();
                if (result.status === 'success') {
                    if (result.sujet && result.sujet.id) {
                        currentSujetData = result.sujet;
                        currentSujetId = result.sujet.id;
                        displaySujet(result.sujet);
                    }
                } else {
                    throw new Error(result.message || 'Failed to create sujet');
                }
            }

            hideTitleInput();

        } catch (error) {
            console.error('Error saving title:', error);
            alert('Failed to save. Please try again.');
        }
    }

    // --- Search Functions ---
    function toggleSearchContainer() {
        const isHidden = searchContainer.classList.contains('hidden');
        if (isHidden) {
            searchContainer.classList.remove('hidden');
            searchInput.focus();
        } else {
            searchContainer.classList.add('hidden');
        }
    }

    function applySearch() {
        const searchTerm = searchInput.value.trim();

        // Check if this is an ID search (number only or #number)
        const idMatch = searchTerm.match(/^#?(\d+)$/);
        if (idMatch) {
            const targetId = parseInt(idMatch[1]);
            jumpToSujetById(targetId);
            return;
        }

        // Regular text search
        activeFilterState.search = searchTerm;

        // Reset offset and clear history when search changes
        currentOffset = 0;
        history.length = 0;

        // Update count and load first result
        updateSujetCount();
        loadNextSujet();

        // Hide search container after applying
        searchContainer.classList.add('hidden');
    }

    async function jumpToSujetById(sujetId) {
        try {
            const response = await fetch(`/get_sujet_by_id/${sujetId}`);
            const data = await response.json();

            if (data.status === 'ok' && data.sujet) {
                // Clear search term and reset to normal browsing
                searchInput.value = '';
                activeFilterState.search = '';

                // Add to history and display the sujet
                history.push(data.sujet.id);
                if (history.length > historySize) history.shift();

                displaySujet(data.sujet);

                // Update back button state
                backButton.disabled = history.length <= 1;

                console.log(`[ID JUMP] Successfully jumped to sujet ID: ${sujetId}`);
            } else {
                alert(`Sujet ID ${sujetId} not found!`);
            }
        } catch (error) {
            console.error('Error jumping to sujet:', error);
            alert(`Error loading sujet ID ${sujetId}`);
        }

        // Hide search container
        searchContainer.classList.add('hidden');
    }

    function clearSearch() {
        searchInput.value = '';
        activeFilterState.search = '';

        // Reset offset and clear history
        currentOffset = 0;
        history.length = 0;

        // Update count and reload
        updateSujetCount();
        loadNextSujet();

        // Hide search container
        searchContainer.classList.add('hidden');
    }

    // Debug function to track navigation
    function debugNavigation(action, sujetId) {
        console.log(`[NAV DEBUG] ${action} - SujetID: ${sujetId}, CurrentOffset: ${currentOffset}`);
    }

    // --- Event Listeners ---
    saveButton.addEventListener('click', () => handleSujetAction('save'));
    skipButton.addEventListener('click', () => loadAdjacentSujet('next'));
    backButton.addEventListener('click', () => loadAdjacentSujet('prev'));

    deleteButton.addEventListener('click', handleDeleteSujet);
    quickSparkButton.addEventListener('click', handleQuickSpark);
    favoriteButton.addEventListener('click', toggleFavorite);
    editTitleButton.addEventListener('click', startEditingTitle);
    saveTitleButton.addEventListener('click', saveTitleAction);
    cancelTitleButton.addEventListener('click', hideTitleInput);
    firstSujetButton.addEventListener('click', () => loadEdgeSujet('first'));
    lastSujetButton.addEventListener('click', () => loadEdgeSujet('last'));

    // Search event listeners
    searchButton.addEventListener('click', toggleSearchContainer);
    searchApplyButton.addEventListener('click', applySearch);
    searchClearButton.addEventListener('click', clearSearch);

    // Allow Enter key in search input to apply search
    searchInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            applySearch();
        }
    });

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

    // Unified Title Input Event Listeners
    newSujetButton.addEventListener('click', startCreatingNewSujet);

    // Allow pressing Enter in the title input to submit
    titleInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            saveTitleAction();
        }
    });

    modeToggleRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            editMode = e.target.value;
            updateToggleAppearance('mode-change'); // Ensure toggles reflect the new mode
            updateSujetCount(); // Update counter display based on new mode
        });
    });

    // --- Initial Load ---
    function initializeApp() {
        renderToggles(tagTogglesDiv, predefinedTags, 'tag');
        renderToggles(personTogglesDiv, predefinedPeople, 'person');

        // Set initial filter state
        activeFilterState.tags = predefinedTags.map(t => t.toLowerCase()); // Default to ALL tags
        activeFilterState.people = predefinedPeople.map(p => p.toLowerCase()); // Default to all people

        updateToggleAppearance('init');
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