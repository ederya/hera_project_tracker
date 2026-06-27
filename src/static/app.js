document.addEventListener('DOMContentLoaded', function() {
    const dateCheckbox = document.getElementById('is_exact_date_active');
    const dateInput = document.getElementById('exact_date');
    const targetPeriodGroup = document.getElementById('target-period-group-add');
    const targetPeriodSelect = document.querySelector('#add-task-form-container .target-period-select');
    
    if (dateCheckbox && dateInput) {
        // Initial state
        dateInput.disabled = !dateCheckbox.checked;
        if (targetPeriodSelect) targetPeriodSelect.disabled = dateCheckbox.checked;
        if (targetPeriodGroup) targetPeriodGroup.style.display = dateCheckbox.checked ? 'none' : 'block';
        
        // On change
        dateCheckbox.addEventListener('change', function() {
            dateInput.disabled = !this.checked;
            if (targetPeriodSelect) targetPeriodSelect.disabled = this.checked;
            if (targetPeriodGroup) targetPeriodGroup.style.display = this.checked ? 'none' : 'block';
            if (!this.checked) {
                dateInput.value = ''; // clear value if disabled
            }
        });
    }

    // Exact Date Checkbox Logic (Edit Task Forms)
    document.querySelectorAll('.edit-exact-date-cb').forEach(cb => {
        // Initial state for edit forms
        const targetId = cb.getAttribute('data-target');
        const selectTargetId = cb.getAttribute('data-select-target');
        const selectTarget = document.getElementById(selectTargetId);
        const groupTargetId = cb.getAttribute('data-group-target');
        const groupTarget = document.getElementById(groupTargetId);
        
        if (selectTarget) {
            selectTarget.disabled = cb.checked;
        }
        if (groupTarget) {
            groupTarget.style.display = cb.checked ? 'none' : 'block';
        }

        cb.addEventListener('change', function() {
            const targetInput = document.getElementById(targetId);
            const targetSelect = document.getElementById(selectTargetId);
            
            if (targetSelect) {
                targetSelect.disabled = this.checked;
            }
            if (groupTarget) {
                groupTarget.style.display = this.checked ? 'none' : 'block';
            }
            if (targetInput) {
                targetInput.disabled = !this.checked;
                if (!this.checked) {
                    targetInput.value = '';
                }
            }
        });
    });

    // Language Toggle Logic (Simple frontend replacement for MVP)
    let currentLang = localStorage.getItem('app_lang') || 'EN';
    
    // Sort Logic
    const sortSelect = document.getElementById('task-sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.set('sort', this.value);
            window.location.search = urlParams.toString();
        });

        // Initialize SortableJS if manual mode is selected
        if (sortSelect.value === 'manual') {
            const openTasksContainer = document.getElementById('open-tasks-container');
            if (openTasksContainer && typeof Sortable !== 'undefined') {
                new Sortable(openTasksContainer, {
                    animation: 150,
                    ghostClass: 'sortable-ghost',
                    onEnd: function () {
                        // Gather new order
                        const taskContainers = openTasksContainer.querySelectorAll('.task-container');
                        const taskOrders = [];
                        taskContainers.forEach((el, index) => {
                            const taskId = el.getAttribute('data-task-id');
                            if (taskId) {
                                taskOrders.push({
                                    id: parseInt(taskId),
                                    order: index
                                });
                            }
                        });

                        // Send to server
                        fetch('/update_task_order', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ task_orders: taskOrders })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status !== 'success') {
                                console.error('Error updating task order');
                            }
                        })
                        .catch(error => console.error('Error:', error));
                    }
                });
            }
        }
    }
    
    const dictionary = {
            'EN': {
                'dashboard_title': 'Hera Project Tracker',
                'add_person': 'Add Person',
                'export_excel': 'Export to Excel',
                'new_person_placeholder': 'Enter person name...',
                'add': 'Add',
                'tasks_for': 'Tasks for',
                'back_to_dashboard': 'Back to Dashboard',
                'add_new_task': 'Add New Task',
                'action_name': 'Action Name',
                'status': 'Status',
                'target_period': 'Target Period',
                'this_week': 'This Week',
                'next_week': 'Next Week',
                'this_month': 'This Month',
                'uncertain_deadline': 'Uncertain Deadline',
                'on_hold': 'On Hold',
                'has_exact_date': 'Has Exact Date?',
                'exact_date': 'Exact Date',
                'close_task': 'Close',
                'reopen_task': 'Re-Open',
                'open': 'Open',
                'closed': 'Closed',
                'confirm_close_msg': 'Are you sure? If it is not fully completed, please keep it open on this screen.',
                'settings': 'Settings',
                'manage_people': 'Manage People',
                'save': 'Save',
                'open_tasks': 'Open Tasks',
                'completed_tasks': 'Completed Tasks',
                'no_tasks': 'No tasks found for this person.',
                'add_task_btn': 'Add Task',
                'show_completed_tasks': 'Completed Tasks',
                'show_open_tasks': 'Open Tasks',
                'confirm_delete_person': 'Are you sure you want to delete this person and ALL their tasks? This action cannot be undone.',
                'confirm_delete_task': 'Are you sure you want to delete this task? This action cannot be undone.',
                'task_details': 'Task Details',
                'back_to_tasks': 'Back to Tasks',
                'edit_task': 'Edit Task',
                'save_changes': 'Save Changes',
                'task_history': 'Task History',
                'no_history': 'No history available for this task.',
                'delete': '🗑️ Delete',
                'sort_by': 'Sort By:',
                'sort_priority': 'By Date Priority',
                'sort_manual': 'Custom',
                'exact_date_badge': 'Exact Date'
            },
            'TR': {
                'dashboard_title': 'Hera Proje Takip Sistemi',
                'add_person': 'Yeni Kişi Ekle',
                'export_excel': 'Excel Çıktısı Al',
                'new_person_placeholder': 'Kişi adı giriniz...',
                'add': 'Ekle',
                'tasks_for': 'Görevler:',
                'back_to_dashboard': 'Ana Sayfaya Dön',
                'add_new_task': 'Yeni Görev Ekle',
                'action_name': 'Aksiyon Adı',
                'status': 'Durum',
                'target_period': 'Hedef Dönem',
                'this_week': 'Bu Hafta',
                'next_week': 'Gelecek Hafta',
                'this_month': 'Bu Ay İçinde',
                'uncertain_deadline': 'Bitiş Tarihi Belirsiz',
                'on_hold': 'Beklemede',
                'has_exact_date': 'Kesin Tarih Var mı?',
                'exact_date': 'Kesin Tarih',
                'close_task': 'Kapat',
                'reopen_task': 'Yeniden Aç',
                'open': 'Açık',
                'closed': 'Kapalı',
                'confirm_close_msg': 'Emin misiniz? Tam olarak tamamlanmadıysa açık olarak bu ekranda tutunuz.',
                'settings': 'Ayarlar',
                'manage_people': 'Kişileri Yönet',
                'save': 'Kaydet',
                'open_tasks': 'Açık Görevler',
                'completed_tasks': 'Bitenler',
                'no_tasks': 'Bu kişi için görev bulunamadı.',
                'add_task_btn': 'Görev Ekle',
                'show_completed_tasks': 'Bitenler',
                'show_open_tasks': 'Açık Görevler',
                'confirm_delete_person': 'Bu kişiyi ve tüm görevlerini kalıcı olarak silmek istediğinize emin misiniz? Bu işlem geri alınamaz.',
                'confirm_delete_task': 'Bu görevi kalıcı olarak silmek istediğinize emin misiniz?',
                'task_details': 'Görev Detayları',
                'back_to_tasks': 'Görevlere Dön',
                'edit_task': 'Görevi Düzenle',
                'save_changes': 'Değişiklikleri Kaydet',
                'task_history': 'Görev Geçmişi',
                'no_history': 'Bu görev için henüz bir geçmiş kaydı yok.',
                'delete': '🗑️ Sil',
                'sort_by': 'Sıralama:',
                'sort_priority': 'Tarih Önceliğine Göre',
                'sort_manual': 'Özel',
                'exact_date_badge': 'Kesin Tarih'
            }
        };

        function applyLanguage(lang) {
            document.querySelectorAll('[data-lang-key]').forEach(el => {
                const key = el.getAttribute('data-lang-key');
                if (dictionary[lang][key]) {
                    if (el.tagName === 'INPUT' && el.type === 'text') {
                        el.placeholder = dictionary[lang][key];
                    } else if (el.tagName === 'INPUT' && (el.type === 'submit' || el.type === 'button')) {
                        el.value = dictionary[lang][key];
                    } else {
                        el.innerText = dictionary[lang][key];
                    }
                }
                
                // Update Excel Export URL if this is the export button
                if (key === 'export_excel' && el.tagName === 'A') {
                    const baseUrl = el.getAttribute('href').split('?')[0];
                    el.setAttribute('href', baseUrl + '?lang=' + lang);
                }
            });
            const langToggleBtn = document.getElementById('lang-toggle');
            if (langToggleBtn) {
                langToggleBtn.innerText = lang === 'EN' ? '🇹🇷 TR' : '🇬🇧 EN';
            }
        }

        // Apply on load
        applyLanguage(currentLang);

        // Toggle on click
        const langToggleBtn = document.getElementById('lang-toggle');
        if (langToggleBtn) {
            langToggleBtn.addEventListener('click', function() {
                currentLang = currentLang === 'EN' ? 'TR' : 'EN';
                localStorage.setItem('app_lang', currentLang);
                applyLanguage(currentLang);
            });
        }

        // Close Task Confirmation
        document.querySelectorAll('.close-task-form').forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!confirm(dictionary[currentLang]['confirm_close_msg'])) {
                    e.preventDefault();
                }
            });
        });

        // Delete Person Confirmation
        document.querySelectorAll('.delete-person-form').forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!confirm(dictionary[currentLang]['confirm_delete_person'])) {
                    e.preventDefault();
                }
            });
        });

        // Delete Task Confirmation
        document.querySelectorAll('.delete-task-form').forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!confirm(dictionary[currentLang]['confirm_delete_task'])) {
                    e.preventDefault();
                }
            });
        });

        // Toggle Add Task Form
        const toggleAddTaskBtn = document.getElementById('toggle-add-task-btn');
        const addTaskFormContainer = document.getElementById('add-task-form-container');
        if (toggleAddTaskBtn && addTaskFormContainer) {
            toggleAddTaskBtn.addEventListener('click', function() {
                if (addTaskFormContainer.style.display === 'none') {
                    addTaskFormContainer.style.display = 'block';
                } else {
                    addTaskFormContainer.style.display = 'none';
                }
            });
        }

        // Toggle Completed Tasks
        const toggleCompletedBtn = document.getElementById('toggle-completed-btn');
        const openTasksContainer = document.getElementById('open-tasks-container');
        const completedTasksContainer = document.getElementById('completed-tasks-container');
        
        if (toggleCompletedBtn && openTasksContainer && completedTasksContainer) {
            toggleCompletedBtn.addEventListener('click', function() {
                if (completedTasksContainer.style.display === 'none') {
                    // Show completed, hide open
                    completedTasksContainer.style.display = 'block';
                    openTasksContainer.style.display = 'none';
                    toggleCompletedBtn.innerText = dictionary[currentLang]['show_open_tasks'];
                    toggleCompletedBtn.setAttribute('data-lang-key', 'show_open_tasks');
                    toggleCompletedBtn.classList.replace('btn-info', 'btn-primary');
                    if (toggleAddTaskBtn) toggleAddTaskBtn.style.display = 'none';
                    if (addTaskFormContainer) addTaskFormContainer.style.display = 'none';
                } else {
                    // Show open, hide completed
                    completedTasksContainer.style.display = 'none';
                    openTasksContainer.style.display = 'block';
                    toggleCompletedBtn.innerText = dictionary[currentLang]['show_completed_tasks'];
                    toggleCompletedBtn.setAttribute('data-lang-key', 'show_completed_tasks');
                    toggleCompletedBtn.classList.replace('btn-primary', 'btn-info');
                    if (toggleAddTaskBtn) toggleAddTaskBtn.style.display = 'inline-block';
                }
            });
        }
});
