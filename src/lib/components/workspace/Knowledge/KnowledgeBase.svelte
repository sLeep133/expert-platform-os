<script lang="ts">
	import Fuse from 'fuse.js';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';

	import { onMount, getContext, onDestroy, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import {
		mobile,
		showSidebar,
		knowledge as _knowledge,
		config,
		user,
		settings
	} from '$lib/stores';

	import {
		updateFileDataContentById,
		uploadFile,
		deleteFileById,
		getFileById
	} from '$lib/apis/files';
	import {
		addFileToKnowledgeById,
		compileKnowledgeById,
		getKnowledgeCompileStatusById,
		getKnowledgeById,
		removeFileFromKnowledgeById,
		resetKnowledgeById,
		updateFileFromKnowledgeById,
		updateKnowledgeById,
		updateKnowledgeAccessGrants,
		searchKnowledgeFilesById,
		getKnowledgeWikiHealth,
		triggerKnowledgeWikiHealthCheck
	} from '$lib/apis/knowledge';
	import { getExperts } from '$lib/apis/experts';
	import { processWeb, processYoutubeVideo } from '$lib/apis/retrieval';

	import { blobToFile, isYoutubeUrl } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Files from './KnowledgeBase/Files.svelte';
	import AddFilesPlaceholder from '$lib/components/AddFilesPlaceholder.svelte';

	import AddContentMenu from './KnowledgeBase/AddContentMenu.svelte';
	import AddTextContentModal from './KnowledgeBase/AddTextContentModal.svelte';

	import SyncConfirmDialog from '../../common/ConfirmDialog.svelte';
	import Drawer from '$lib/components/common/Drawer.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import FilesOverlay from '$lib/components/chat/MessageInput/FilesOverlay.svelte';
	import DropdownOptions from '$lib/components/common/DropdownOptions.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import AttachWebpageModal from '$lib/components/chat/MessageInput/AttachWebpageModal.svelte';

	let largeScreen = true;

	let pane;
	let showSidepanel = true;

	let showAddWebpageModal = false;
	let showAddTextContentModal = false;

	let showSyncConfirmModal = false;
	let showAccessControlModal = false;

	let minSize = 0;
	type Knowledge = {
		id: string;
		name: string;
		description: string;
		data: {
			file_ids: string[];
		};
		files: any[];
		access_grants?: any[];
		write_access?: boolean;
		meta?: {
			expert_platform?: {
				compile?: {
					job_id?: string | null;
					status?: string;
					started_at?: number | null;
					finished_at?: number | null;
					error?: string | null;
					asset_count?: number;
					page_count?: number;
				};
				wiki?: {
					pages?: Array<{
						id: string;
						title: string;
						source_file_id: string;
						source_name: string;
						summary: string;
						excerpt: string;
						word_count: number;
						updated_at: number;
					}>;
				};
			};
		};
	};

	let id = null;
	let knowledge: Knowledge | null = null;
	let knowledgeId = null;

	let selectedFileId = null;
	let selectedFile = null;
	let selectedFileContent = '';

	let inputFiles = null;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let viewOption = null;
	let sortKey = null;
	let direction = null;

	let currentPage = 1;
	let fileItems = null;
	let fileItemsTotal = null;
	let compileStarting = false;
	let compileStatus = {
		status: 'idle',
		job_id: null,
		started_at: null,
		finished_at: null,
		error: null,
		asset_count: 0,
		page_count: 0
	};
	let wikiPages = [];
	let compilePollingTimer: ReturnType<typeof setInterval> | null = null;
	let linkedExperts = [];
	let loadingLinkedExperts = false;
	let collapsedGroups: Record<string, boolean> = {};
	let healthReport: any = null;
	let checkingHealth = false;

	const computeGroupedPages = (pages: any[]) => {
		const groups: Record<string, { label: string; pages: any[] }> = {
			entity: { label: '实体 (Entity)', pages: [] },
			concept: { label: '概念 (Concept)', pages: [] },
			topic: { label: '主题 (Topic)', pages: [] },
			comparison: { label: '对比 (Comparison)', pages: [] },
			query: { label: '查询 (Query)', pages: [] },
			other: { label: '其他', pages: [] }
		};
		for (const page of pages) {
			const type = page.page_type || 'other';
			if (groups[type]) {
				groups[type].pages.push(page);
			} else {
				groups.other.pages.push(page);
			}
		}
		return Object.entries(groups)
			.filter(([, g]) => g.pages.length > 0)
			.map(([key, g]) => ({
				key,
				label: g.label,
				pages: g.pages,
				collapsed: collapsedGroups[key] ?? false
			}));
	};

	const reset = () => {
		currentPage = 1;
	};

	const applyCompilePayload = (payload) => {
		compileStatus = {
			status: payload?.compile?.status ?? 'idle',
			job_id: payload?.compile?.job_id ?? null,
			started_at: payload?.compile?.started_at ?? null,
			finished_at: payload?.compile?.finished_at ?? null,
			error: payload?.compile?.error ?? null,
			asset_count: payload?.compile?.asset_count ?? 0,
			page_count: payload?.compile?.page_count ?? 0
		};
		wikiPages = payload?.wiki_pages ?? [];

		if (knowledge) {
			knowledge = {
				...knowledge,
				meta: {
					...(knowledge.meta ?? {}),
					expert_platform: {
						...(knowledge.meta?.expert_platform ?? {}),
						compile: { ...compileStatus },
						wiki: {
							...(knowledge.meta?.expert_platform?.wiki ?? {}),
							pages: [...wikiPages]
						}
					}
				}
			};
		}
	};

	const syncCompileFromKnowledge = () => {
		const expertPlatform = knowledge?.meta?.expert_platform ?? {};
		compileStatus = {
			status: expertPlatform?.compile?.status ?? 'idle',
			job_id: expertPlatform?.compile?.job_id ?? null,
			started_at: expertPlatform?.compile?.started_at ?? null,
			finished_at: expertPlatform?.compile?.finished_at ?? null,
			error: expertPlatform?.compile?.error ?? null,
			asset_count: expertPlatform?.compile?.asset_count ?? 0,
			page_count: expertPlatform?.compile?.page_count ?? 0
		};
		wikiPages = expertPlatform?.wiki?.pages ?? [];
	};

	const stopCompilePolling = () => {
		if (compilePollingTimer) {
			clearInterval(compilePollingTimer);
			compilePollingTimer = null;
		}
	};

	const refreshCompileStatus = async ({ silent = false } = {}) => {
		if (!knowledgeId) return null;

		const res = await getKnowledgeCompileStatusById(localStorage.token, knowledgeId).catch((e) => {
			if (!silent) {
				toast.error(`${e}`);
			}
			return null;
		});

		if (res) {
			applyCompilePayload(res);
			if (!['queued', 'running'].includes(res?.compile?.status ?? '')) {
				stopCompilePolling();
			}
		}

		return res;
	};

	const startCompilePolling = () => {
		if (compilePollingTimer || !knowledgeId) return;

		compilePollingTimer = setInterval(async () => {
			const res = await refreshCompileStatus({ silent: true });
			if (!['queued', 'running'].includes(res?.compile?.status ?? '')) {
				stopCompilePolling();
			}
		}, 2000);
	};

	const compileKnowledgeHandler = async () => {
		if (!knowledge?.write_access || !knowledgeId || compileStarting) return;

		compileStarting = true;
		const res = await compileKnowledgeById(localStorage.token, knowledgeId).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		compileStarting = false;

		if (res) {
			applyCompilePayload(res);
			if (['queued', 'running'].includes(res?.compile?.status ?? '')) {
				toast.success($i18n.t('Knowledge compile started'));
				startCompilePolling();
			}
		}
	};

	const loadLinkedExperts = async () => {
		if (!knowledgeId) return;

		loadingLinkedExperts = true;
		try {
			const experts = await getExperts(localStorage.token);
			linkedExperts = (experts ?? []).filter((expert) =>
				(expert.knowledge_spaces ?? []).includes(knowledgeId)
			);
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			loadingLinkedExperts = false;
		}
	};

	const checkHealth = async () => {
		if (!knowledgeId) return;
		checkingHealth = true;
		try {
			const report = await triggerKnowledgeWikiHealthCheck(localStorage.token, knowledgeId);
			healthReport = report;
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			checkingHealth = false;
		}
	};

	const init = async () => {
		reset();
		await getItemsPage();
	};

	// Debounce only query changes
	$: if (query !== undefined) {
		clearTimeout(searchDebounceTimer);

		searchDebounceTimer = setTimeout(() => {
			getItemsPage();
		}, 300);
	}

	// Immediate response to filter/pagination changes
	$: if (
		knowledgeId !== null &&
		viewOption !== undefined &&
		sortKey !== undefined &&
		direction !== undefined &&
		currentPage !== undefined
	) {
		getItemsPage();
	}

	$: if (
		query !== undefined &&
		viewOption !== undefined &&
		sortKey !== undefined &&
		direction !== undefined
	) {
		reset();
	}

	const getItemsPage = async () => {
		if (knowledgeId === null) return;

		fileItems = null;
		fileItemsTotal = null;

		if (sortKey === null) {
			direction = null;
		}

		const res = await searchKnowledgeFilesById(
			localStorage.token,
			knowledge.id,
			query,
			viewOption,
			sortKey,
			direction,
			currentPage
		).catch(() => {
			return null;
		});

		if (res) {
			fileItems = res.items;
			fileItemsTotal = res.total;
		}
		return res;
	};

	const fileSelectHandler = async (file) => {
		try {
			selectedFile = file;
			selectedFileContent = selectedFile?.data?.content || '';
		} catch (e) {
			toast.error($i18n.t('Failed to load file content.'));
		}
	};

	const createFileFromText = (name, content) => {
		const blob = new Blob([content], { type: 'text/plain' });
		const file = blobToFile(blob, `${name}.txt`);

		console.log(file);
		return file;
	};

	const uploadWeb = async (urls) => {
		if (!Array.isArray(urls)) {
			urls = [urls];
		}

		const newFileItems = urls.map((url) => ({
			type: 'file',
			file: '',
			id: null,
			url: url,
			name: url,
			size: null,
			status: 'uploading',
			error: '',
			itemId: uuidv4()
		}));

		// Display all items at once
		fileItems = [...newFileItems, ...(fileItems ?? [])];

		for (const fileItem of newFileItems) {
			try {
				console.log(fileItem);
				const res = await processWeb(localStorage.token, '', fileItem.url, false).catch((e) => {
					console.error('Error processing web URL:', e);
					return null;
				});

				if (res) {
					console.log(res);
					const file = createFileFromText(
						// Use URL as filename, sanitized
						fileItem.url
							.replace(/[^a-z0-9]/gi, '_')
							.toLowerCase()
							.slice(0, 50),
						res.content
					);

					const uploadedFile = await uploadFile(localStorage.token, file).catch((e) => {
						toast.error(`${e}`);
						return null;
					});

					if (uploadedFile) {
						console.log(uploadedFile);
						fileItems = fileItems.map((item) => {
							if (item.itemId === fileItem.itemId) {
								item.id = uploadedFile.id;
							}
							return item;
						});

						if (uploadedFile.error) {
							console.warn('File upload warning:', uploadedFile.error);
							toast.warning(uploadedFile.error);
							fileItems = fileItems.filter((file) => file.id !== uploadedFile.id);
						} else {
							await addFileHandler(uploadedFile.id);
						}
					} else {
						toast.error($i18n.t('Failed to upload file.'));
					}
				} else {
					// remove the item from fileItems
					fileItems = fileItems.filter((item) => item.itemId !== fileItem.itemId);
					toast.error($i18n.t('Failed to process URL: {{url}}', { url: fileItem.url }));
				}
			} catch (e) {
				// remove the item from fileItems
				fileItems = fileItems.filter((item) => item.itemId !== fileItem.itemId);
				toast.error(`${e}`);
			}
		}
	};

	const uploadFileHandler = async (file) => {
		console.log(file);

		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			size: file.size,
			status: 'uploading',
			error: '',
			itemId: uuidv4()
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		if (
			($config?.file?.max_size ?? null) !== null &&
			file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
		) {
			console.log('File exceeds max size limit:', {
				fileSize: file.size,
				maxSize: ($config?.file?.max_size ?? 0) * 1024 * 1024
			});
			toast.error(
				$i18n.t(`File size should not exceed {{maxSize}} MB.`, {
					maxSize: $config?.file?.max_size
				})
			);
			return;
		}

		fileItems = [fileItem, ...(fileItems ?? [])];
		try {
			let metadata = {
				knowledge_id: knowledge.id,
				// If the file is an audio file, provide the language for STT.
				...((file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
					? {
							language: $settings?.audio?.stt?.language
						}
					: {})
			};

			const uploadedFile = await uploadFile(localStorage.token, file, metadata).catch((e) => {
				toast.error(`${e}`);
				return null;
			});

			if (uploadedFile) {
				console.log(uploadedFile);
				fileItems = fileItems.map((item) => {
					if (item.itemId === fileItem.itemId) {
						item.id = uploadedFile.id;
					}
					return item;
				});

				if (uploadedFile.error) {
					console.warn('File upload warning:', uploadedFile.error);
					toast.warning(uploadedFile.error);
					fileItems = fileItems.filter((file) => file.id !== uploadedFile.id);
				} else {
					await addFileHandler(uploadedFile.id);
				}
			} else {
				toast.error($i18n.t('Failed to upload file.'));
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const uploadDirectoryHandler = async () => {
		// Check if File System Access API is supported
		const isFileSystemAccessSupported = 'showDirectoryPicker' in window;

		try {
			if (isFileSystemAccessSupported) {
				// Modern browsers (Chrome, Edge) implementation
				await handleModernBrowserUpload();
			} else {
				// Firefox fallback
				await handleFirefoxUpload();
			}
		} catch (error) {
			handleUploadError(error);
		}
	};

	// Helper function to check if a path contains hidden folders
	const hasHiddenFolder = (path) => {
		return path.split('/').some((part) => part.startsWith('.'));
	};

	// Modern browsers implementation using File System Access API
	const handleModernBrowserUpload = async () => {
		const dirHandle = await window.showDirectoryPicker();
		let totalFiles = 0;
		let uploadedFiles = 0;

		// Function to update the UI with the progress
		const updateProgress = () => {
			const percentage = (uploadedFiles / totalFiles) * 100;
			toast.info(
				$i18n.t('Upload Progress: {{uploadedFiles}}/{{totalFiles}} ({{percentage}}%)', {
					uploadedFiles: uploadedFiles,
					totalFiles: totalFiles,
					percentage: percentage.toFixed(2)
				})
			);
		};

		// Recursive function to count all files excluding hidden ones
		async function countFiles(dirHandle) {
			for await (const entry of dirHandle.values()) {
				// Skip hidden files and directories
				if (entry.name.startsWith('.')) continue;

				if (entry.kind === 'file') {
					totalFiles++;
				} else if (entry.kind === 'directory') {
					// Only process non-hidden directories
					if (!entry.name.startsWith('.')) {
						await countFiles(entry);
					}
				}
			}
		}

		// Recursive function to process directories excluding hidden files and folders
		async function processDirectory(dirHandle, path = '') {
			for await (const entry of dirHandle.values()) {
				// Skip hidden files and directories
				if (entry.name.startsWith('.')) continue;

				const entryPath = path ? `${path}/${entry.name}` : entry.name;

				// Skip if the path contains any hidden folders
				if (hasHiddenFolder(entryPath)) continue;

				if (entry.kind === 'file') {
					const file = await entry.getFile();
					const fileWithPath = new File([file], entryPath, { type: file.type });

					await uploadFileHandler(fileWithPath);
					uploadedFiles++;
					updateProgress();
				} else if (entry.kind === 'directory') {
					// Only process non-hidden directories
					if (!entry.name.startsWith('.')) {
						await processDirectory(entry, entryPath);
					}
				}
			}
		}

		await countFiles(dirHandle);
		updateProgress();

		if (totalFiles > 0) {
			await processDirectory(dirHandle);
		} else {
			console.log('No files to upload.');
		}
	};

	// Firefox fallback implementation using traditional file input
	const handleFirefoxUpload = async () => {
		return new Promise((resolve, reject) => {
			// Create hidden file input
			const input = document.createElement('input');
			input.type = 'file';
			input.webkitdirectory = true;
			input.directory = true;
			input.multiple = true;
			input.style.display = 'none';

			// Add input to DOM temporarily
			document.body.appendChild(input);

			input.onchange = async () => {
				try {
					const files = Array.from(input.files)
						// Filter out files from hidden folders
						.filter((file) => !hasHiddenFolder(file.webkitRelativePath));

					let totalFiles = files.length;
					let uploadedFiles = 0;

					// Function to update the UI with the progress
					const updateProgress = () => {
						const percentage = (uploadedFiles / totalFiles) * 100;
						toast.info(
							$i18n.t('Upload Progress: {{uploadedFiles}}/{{totalFiles}} ({{percentage}}%)', {
								uploadedFiles: uploadedFiles,
								totalFiles: totalFiles,
								percentage: percentage.toFixed(2)
							})
						);
					};

					updateProgress();

					// Process all files
					for (const file of files) {
						// Skip hidden files (additional check)
						if (!file.name.startsWith('.')) {
							const relativePath = file.webkitRelativePath || file.name;
							const fileWithPath = new File([file], relativePath, { type: file.type });

							await uploadFileHandler(fileWithPath);
							uploadedFiles++;
							updateProgress();
						}
					}

					// Clean up
					document.body.removeChild(input);
					resolve();
				} catch (error) {
					reject(error);
				}
			};

			input.onerror = (error) => {
				document.body.removeChild(input);
				reject(error);
			};

			// Trigger file picker
			input.click();
		});
	};

	// Error handler
	const handleUploadError = (error) => {
		if (error.name === 'AbortError') {
			toast.info($i18n.t('Directory selection was cancelled'));
		} else {
			toast.error($i18n.t('Error accessing directory'));
			console.error('Directory access error:', error);
		}
	};

	// Helper function to maintain file paths within zip
	const syncDirectoryHandler = async () => {
		if (fileItems.length > 0) {
			const res = await resetKnowledgeById(localStorage.token, id).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				fileItems = [];
				toast.success($i18n.t('Knowledge reset successfully.'));

				// Upload directory
				uploadDirectoryHandler();
			}
		} else {
			uploadDirectoryHandler();
		}
	};

	const addFileHandler = async (fileId) => {
		const res = await addFileToKnowledgeById(localStorage.token, id, fileId).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('File added successfully.'));
			init();
		} else {
			toast.error($i18n.t('Failed to add file.'));
			fileItems = fileItems.filter((file) => file.id !== fileId);
		}
	};

	const deleteFileHandler = async (fileId) => {
		try {
			console.log('Starting file deletion process for:', fileId);

			// Remove from knowledge base only
			const res = await removeFileFromKnowledgeById(localStorage.token, id, fileId);
			console.log('Knowledge base updated:', res);

			if (res) {
				toast.success($i18n.t('File removed successfully.'));
				await init();
			}
		} catch (e) {
			console.error('Error in deleteFileHandler:', e);
			toast.error(`${e}`);
		}
	};

	let debounceTimeout = null;
	let mediaQuery;

	let dragged = false;
	let isSaving = false;

	const updateFileContentHandler = async () => {
		if (isSaving) {
			console.log('Save operation already in progress, skipping...');
			return;
		}

		isSaving = true;

		try {
			const res = await updateFileDataContentById(
				localStorage.token,
				selectedFile.id,
				selectedFileContent
			).catch((e) => {
				toast.error(`${e}`);
				return null;
			});

			if (res) {
				toast.success($i18n.t('File content updated successfully.'));

				selectedFileId = null;
				selectedFile = null;
				selectedFileContent = '';

				await init();
			}
		} finally {
			isSaving = false;
		}
	};

	const changeDebounceHandler = () => {
		console.log('debounce');
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
		}

		debounceTimeout = setTimeout(async () => {
			if (knowledge.name.trim() === '' || knowledge.description.trim() === '') {
				toast.error($i18n.t('Please fill in all fields.'));
				return;
			}

			const res = await updateKnowledgeById(localStorage.token, id, {
				...knowledge,
				name: knowledge.name,
				description: knowledge.description,
				access_grants: knowledge.access_grants ?? []
			}).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				toast.success($i18n.t('Knowledge updated successfully'));
			}
		}, 1000);
	};

	const handleMediaQuery = async (e) => {
		if (e.matches) {
			largeScreen = true;
		} else {
			largeScreen = false;
		}
	};

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being draggedOver.
		if (e.dataTransfer?.types?.includes('Files')) {
			dragged = true;
		} else {
			dragged = false;
		}
	};

	const onDragLeave = () => {
		dragged = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		dragged = false;

		if (!knowledge?.write_access) {
			toast.error($i18n.t('You do not have permission to upload files to this knowledge base.'));
			return;
		}

		const handleUploadingFileFolder = (items) => {
			for (const item of items) {
				if (item.isFile) {
					item.file((file) => {
						uploadFileHandler(file);
					});
					continue;
				}

				// Not sure why you have to call webkitGetAsEntry and isDirectory seperate, but it won't work if you try item.webkitGetAsEntry().isDirectory
				const wkentry = item.webkitGetAsEntry();
				const isDirectory = wkentry.isDirectory;
				if (isDirectory) {
					// Read the directory
					wkentry.createReader().readEntries(
						(entries) => {
							handleUploadingFileFolder(entries);
						},
						(error) => {
							console.error('Error reading directory entries:', error);
						}
					);
				} else {
					toast.info($i18n.t('Uploading file...'));
					uploadFileHandler(item.getAsFile());
					toast.success($i18n.t('File uploaded!'));
				}
			}
		};

		if (e.dataTransfer?.types?.includes('Files')) {
			if (e.dataTransfer?.files) {
				const inputItems = e.dataTransfer?.items;

				if (inputItems && inputItems.length > 0) {
					handleUploadingFileFolder(inputItems);
				} else {
					toast.error($i18n.t(`File not found.`));
				}
			}
		}
	};

	onMount(async () => {
		// listen to resize 1024px
		mediaQuery = window.matchMedia('(min-width: 1024px)');

		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);

		// Select the container element you want to observe
		const container = document.getElementById('collection-container');

		// initialize the minSize based on the container width
		minSize = !largeScreen ? 100 : Math.floor((300 / container.clientWidth) * 100);

		// Create a new ResizeObserver instance
		const resizeObserver = new ResizeObserver((entries) => {
			for (let entry of entries) {
				const width = entry.contentRect.width;
				// calculate the percentage of 300
				const percentage = (300 / width) * 100;
				// set the minSize to the percentage, must be an integer
				minSize = !largeScreen ? 100 : Math.floor(percentage);

				if (showSidepanel) {
					if (pane && pane.isExpanded() && pane.getSize() < minSize) {
						pane.resize(minSize);
					}
				}
			}
		});

		// Start observing the container's size changes
		resizeObserver.observe(container);

		if (pane) {
			pane.expand();
		}

		id = $page.params.id;
		const res = await getKnowledgeById(localStorage.token, id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			knowledge = res;
			if (!Array.isArray(knowledge?.access_grants)) {
				knowledge.access_grants = [];
			}
			knowledgeId = knowledge?.id;
			syncCompileFromKnowledge();
			await loadLinkedExperts();
			if (['queued', 'running'].includes(compileStatus.status ?? '')) {
				startCompilePolling();
			}
		} else {
			goto('/workspace/knowledge');
		}

		const dropZone = document.querySelector('body');
		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
		stopCompilePolling();
		mediaQuery?.removeEventListener('change', handleMediaQuery);
		const dropZone = document.querySelector('body');
		dropZone?.removeEventListener('dragover', onDragOver);
		dropZone?.removeEventListener('drop', onDrop);
		dropZone?.removeEventListener('dragleave', onDragLeave);
	});

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};
</script>

<FilesOverlay show={dragged} />
<SyncConfirmDialog
	bind:show={showSyncConfirmModal}
	message={$i18n.t(
		'This will reset the knowledge base and sync all files. Do you wish to continue?'
	)}
	on:confirm={() => {
		syncDirectoryHandler();
	}}
/>

<AttachWebpageModal
	bind:show={showAddWebpageModal}
	onSubmit={async (e) => {
		uploadWeb(e.data);
	}}
/>

<AddTextContentModal
	bind:show={showAddTextContentModal}
	on:submit={(e) => {
		const file = createFileFromText(e.detail.name, e.detail.content);
		uploadFileHandler(file);
	}}
/>

<input
	id="files-input"
	bind:files={inputFiles}
	type="file"
	multiple
	hidden
	on:change={async () => {
		if (inputFiles && inputFiles.length > 0) {
			for (const file of inputFiles) {
				await uploadFileHandler(file);
			}

			inputFiles = null;
			const fileInputElement = document.getElementById('files-input');

			if (fileInputElement) {
				fileInputElement.value = '';
			}
		} else {
			toast.error($i18n.t(`File not found.`));
		}
	}}
/>

<div class="flex flex-col w-full h-full min-h-full" id="collection-container">
	{#if id && knowledge}
		<AccessControlModal
			bind:show={showAccessControlModal}
			bind:accessGrants={knowledge.access_grants}
			share={$user?.permissions?.sharing?.knowledge || $user?.role === 'admin'}
			sharePublic={$user?.permissions?.sharing?.public_knowledge || $user?.role === 'admin'}
			shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) ||
				$user?.role === 'admin'}
			onChange={async () => {
				try {
					await updateKnowledgeAccessGrants(localStorage.token, id, knowledge.access_grants ?? []);
					toast.success($i18n.t('Saved'));
				} catch (error) {
					toast.error(`${error}`);
				}
			}}
			accessRoles={['read', 'write']}
		/>
		<div class="w-full px-2">
			<div class=" flex w-full">
				<div class="flex-1">
					<div class="flex items-center justify-between w-full">
						<div class="w-full flex justify-between items-center">
							<input
								type="text"
								class="text-left w-full text-lg bg-transparent outline-hidden flex-1"
								bind:value={knowledge.name}
								aria-label={$i18n.t('Knowledge Name')}
								placeholder={$i18n.t('Knowledge Name')}
								disabled={!knowledge?.write_access}
								on:input={() => {
									changeDebounceHandler();
								}}
							/>

							<div class="shrink-0 mr-2.5">
								{#if fileItemsTotal}
									<div class="text-xs text-gray-500">
										<!-- {$i18n.t('{{COUNT}} files')} -->
										{$i18n.t('{{COUNT}} files', {
											COUNT: fileItemsTotal
										})}
									</div>
								{/if}
							</div>
						</div>

						{#if knowledge?.write_access}
							<div class="self-center shrink-0">
								<button
									class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
									type="button"
									on:click={() => {
										showAccessControlModal = true;
									}}
								>
									<LockClosed strokeWidth="2.5" className="size-3.5" />

									<div class="text-sm font-medium shrink-0">
										{$i18n.t('Access')}
									</div>
								</button>
							</div>
						{:else}
							<div class="text-xs shrink-0 text-gray-500">
								{$i18n.t('Read Only')}
							</div>
						{/if}
					</div>

					<div class="flex w-full">
						<input
							type="text"
							class="text-left text-xs w-full text-gray-500 bg-transparent outline-hidden"
							bind:value={knowledge.description}
							aria-label={$i18n.t('Knowledge Description')}
							placeholder={$i18n.t('Knowledge Description')}
							disabled={!knowledge?.write_access}
							on:input={() => {
								changeDebounceHandler();
							}}
						/>
					</div>
				</div>
			</div>

			<div class="mt-3 rounded-2xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 px-3 py-3">
				<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
					<div class="space-y-1">
						<div class="text-sm font-medium text-gray-900 dark:text-gray-100">Wiki 编译</div>
						<div class="flex flex-wrap items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
							<div class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-900 text-gray-700 dark:text-gray-200">
								状态：{compileStatus.status === 'queued'
									? '排队中'
									: compileStatus.status === 'running'
										? '编译中'
										: compileStatus.status === 'completed'
											? '已完成'
											: compileStatus.status === 'failed'
												? '失败'
												: '未开始'}
							</div>
							<div>资源：{compileStatus.asset_count}</div>
							<div>页面：{compileStatus.page_count}</div>
						</div>

						{#if compileStatus.error}
							<div class="text-xs text-red-500">
								{compileStatus.error}
							</div>
						{/if}
					</div>

					{#if knowledge?.write_access}
						<div class="shrink-0">
							<button
								class="px-3 py-2 rounded-xl text-sm bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
								type="button"
								disabled={compileStarting || ['queued', 'running'].includes(compileStatus.status)}
								on:click={compileKnowledgeHandler}
							>
								{#if compileStarting || ['queued', 'running'].includes(compileStatus.status)}
									<Spinner className="size-4" />
								{/if}
								编译 Wiki
							</button>
						</div>
					{/if}
				</div>

				{#if wikiPages.length > 0}
					{@const groupedPages = computeGroupedPages(wikiPages)}
					<div class="mt-3 space-y-2">
						{#each groupedPages as group}
							{@const isCollapsed = collapsedGroups[group.key] ?? false}
							<div class="rounded-xl border border-gray-100 dark:border-gray-800">
								<button
									type="button"
									class="w-full flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-900 rounded-t-xl transition"
									on:click={() => {
										collapsedGroups = { ...collapsedGroups, [group.key]: !collapsedGroups[group.key] };
									}}
								>
									<span class="text-xs text-gray-400">{isCollapsed ? '▶' : '▼'}</span>
									<span>{group.label}</span>
									<span class="text-xs text-gray-400">({group.pages.length})</span>
								</button>
								{#if !isCollapsed}
									<div class="grid grid-cols-1 xl:grid-cols-2 gap-2 p-3 pt-1">
										{#each group.pages as page}
											<div class="rounded-lg border border-gray-100 dark:border-gray-900 px-3 py-2">
												<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
													{page.title}
												</div>
												<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
													{page.source_name} - {page.word_count || 0} 字
												</div>
												<div class="mt-2 text-sm text-gray-600 dark:text-gray-300 line-clamp-3">
													{page.summary || ''}
												</div>
											</div>
										{/each}
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else if compileStatus.status === 'completed'}
					<div class="mt-3 text-xs text-gray-500 dark:text-gray-400">
						编译已完成，但当前文件还没有生成可用的 Wiki 页面。
					</div>
				{/if}
			</div>
				<div class="mt-3 rounded-2xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 px-3 py-3">
					<div class="flex items-center justify-between gap-3">
						<div>
							<div class="text-sm font-medium text-gray-900 dark:text-gray-100">Wiki 健康检查</div>
							<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
								检测断链、孤儿页和重复页，维护知识图谱质量。
							</div>
						</div>
						<button
							class="px-3 py-2 rounded-xl text-sm border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900 transition disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
							disabled={checkingHealth}
							on:click={checkHealth}
						>
							{#if checkingHealth}
								<Spinner className="size-4" />
							{/if}
							运行检查
						</button>
					</div>

					<div class="mt-2 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/50 rounded-lg p-2.5 space-y-1.5">
						<div class="font-medium text-gray-700 dark:text-gray-200">什么时候应该点「运行检查」？</div>
						<div>• 每次编译完 Wiki 后，点一下看看生成的页面有没有问题。</div>
						<div>• 往知识库里新增或删除文件后，也建议检查一下。</div>
						<div class="font-medium text-gray-700 dark:text-gray-200 mt-1">三个问题分别是什么意思？</div>
						<div>
							<span class="font-medium">断链（红色）：</span>某个页面里写了 <code class="text-[11px] bg-gray-200 dark:bg-gray-700 px-1 rounded">[[另一个页面]]</code>，但「另一个页面」并不存在。解决办法：把链接改成存在的页面名，或者创建这个缺失的页面。
						</div>
						<div>
							<span class="font-medium">孤岛页面（黄色）：</span>这个页面存在，但没有任何其他页面链接到它，就像一座孤岛，很难被找到。解决办法：在相关的其他页面里加上 <code class="text-[11px] bg-gray-200 dark:bg-gray-700 px-1 rounded">[[这个页面名]]</code> 链接过来。
						</div>
						<div>
							<span class="font-medium">重复页面（蓝色）：</span>有两个页面的文件名几乎一样。解决办法：删掉其中一个，或把两个合并成一个页面。
						</div>
					</div>

					{#if healthReport}
						<div class="mt-3 flex flex-wrap gap-2 text-xs">
							<div class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-900 text-gray-700 dark:text-gray-200">
								总页面 {healthReport.total_pages ?? 0}
							</div>
							<div class="px-2 py-1 rounded-full {healthReport.issues?.length ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-200' : 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-200'}">
								问题 {healthReport.issues?.length ?? 0} 个
							</div>
						</div>

						{#if healthReport.issues?.length > 0}
							<div class="mt-3 space-y-2">
								{#each healthReport.issues as issue}
									<div class="rounded-xl border border-gray-100 dark:border-gray-900 p-3">
										<div class="flex items-center gap-2">
											<span class="text-xs px-2 py-0.5 rounded-full {issue.severity === 'high' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-200' : issue.severity === 'medium' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-200' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-200'}">
												{issue.severity}
											</span>
											<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
												{issue.rule_id === 'orphan-page' ? '孤岛页面' : issue.rule_id === 'duplicate-page' ? '重复页面' : issue.rule_id === 'broken-link' ? '断链' : issue.rule_id}
											</span>
										</div>
										{#if issue.pages}
											<div class="mt-2 text-xs text-gray-500 dark:text-gray-400 space-y-1">
												{#each issue.pages as page}
													<div class="truncate">{page}</div>
												{/each}
											</div>
										{/if}
										{#if issue.links}
											<div class="mt-2 text-xs text-gray-500 dark:text-gray-400 space-y-1">
												{#each issue.links as link}
													<div class="truncate">{link.from} → {link.link}</div>
												{/each}
											</div>
										<div class="mt-2 text-[11px] text-gray-400 dark:text-gray-500">
											{#if issue.rule_id === 'broken-link'}
												建议：把断链改成已存在的页面名，或创建这个缺失的页面。
											{:else if issue.rule_id === 'orphan-page'}
												建议：在其他相关页面里加上 [[页面名]] 链接到这个页面。
											{:else if issue.rule_id === 'duplicate-page'}
												建议：保留一个页面，删除或合并另一个重复的页面。
											{/if}
										</div>
										{/if}
									</div>
								{/each}
							</div>
						{:else}
							<div class="mt-3 text-xs text-green-600 dark:text-green-400">
								Wiki 健康状态良好，未发现问题。
							</div>
						{/if}
					{/if}
				</div>


			<div class="mt-3 rounded-2xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 px-3 py-3">
				<div class="flex items-center justify-between gap-3">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-gray-100">关联专家</div>
						<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
							这里显示已使用当前知识空间的专家；请先到“专家”页面创建专家，再在“知识关联”里选中当前知识空间。
						</div>
					</div>
					{#if loadingLinkedExperts}
						<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
							<Spinner className="size-3.5" />
							<span>加载中</span>
						</div>
					{/if}
				</div>

				{#if linkedExperts.length > 0}
					<div class="mt-3 grid grid-cols-1 xl:grid-cols-2 gap-2">
						{#each linkedExperts as expert}
							<button
								type="button"
								class="w-full text-left rounded-xl border border-gray-100 dark:border-gray-900 px-3 py-3 hover:bg-gray-50 dark:hover:bg-gray-900 transition"
								on:click={() => goto(`/workspace/experts/edit?id=${expert.id}`)}
							>
								<div class="flex items-start justify-between gap-3">
									<div>
										<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
											{expert.name}
										</div>
										{#if expert.description}
											<div class="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
												{expert.description}
											</div>
										{/if}
									</div>
									<div class="text-[11px] px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-300">
										{expert.visibility === 'shared' ? '共享' : expert.visibility === 'private' ? '私有' : expert.visibility}
									</div>
								</div>
								{#if expert.knowledge_pinned_pages?.length > 0}
									<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
										已固定 {expert.knowledge_pinned_pages.length} 个重点页面
									</div>
								{/if}
							</button>
						{/each}
					</div>
				{:else if !loadingLinkedExperts}
					<div class="mt-3 text-xs text-gray-500 dark:text-gray-400">
						当前还没有专家关联这个知识空间。
					</div>
				{/if}
			</div>
		</div>

		<div
			class="mt-2 mb-2.5 py-2 -mx-0 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30 flex-1"
		>
			<div class="px-3.5 flex flex-1 items-center w-full space-x-2 py-0.5 pb-2">
				<div class="flex flex-1 items-center">
					<div class=" self-center ml-1 mr-3">
						<Search className="size-3.5" />
					</div>
					<input
						class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
						bind:value={query}
						aria-label="搜索知识内容"
						placeholder="搜索知识内容"
						on:focus={() => {
							selectedFileId = null;
						}}
					/>

					{#if knowledge?.write_access}
						<div>
							<AddContentMenu
								onUpload={(data) => {
									if (data.type === 'directory') {
										uploadDirectoryHandler();
									} else if (data.type === 'web') {
										showAddWebpageModal = true;
									} else if (data.type === 'text') {
										showAddTextContentModal = true;
									} else {
										document.getElementById('files-input').click();
									}
								}}
								onSync={() => {
									showSyncConfirmModal = true;
								}}
							/>
						</div>
					{/if}
				</div>
			</div>

			<div class="px-3 flex justify-between">
				<div
					class="flex w-full bg-transparent overflow-x-auto scrollbar-none"
					on:wheel={(e) => {
						if (e.deltaY !== 0) {
							e.preventDefault();
							e.currentTarget.scrollLeft += e.deltaY;
						}
					}}
				>
					<div
						class="flex gap-3 w-fit text-center text-sm rounded-full bg-transparent px-0.5 whitespace-nowrap"
					>
						<DropdownOptions
							align="start"
							className="flex shrink-0 items-center gap-2 px-3 py-1.5 text-sm bg-gray-50 dark:bg-gray-850 rounded-xl placeholder-gray-400 outline-hidden focus:outline-hidden"
							bind:value={viewOption}
							items={[
								{ value: null, label: $i18n.t('All') },
								{ value: 'created', label: $i18n.t('Created by you') },
								{ value: 'shared', label: $i18n.t('Shared with you') }
							]}
							onChange={(value) => {
								if (value) {
									localStorage.workspaceViewOption = value;
								} else {
									delete localStorage.workspaceViewOption;
								}
							}}
						/>

						<DropdownOptions
							align="start"
							bind:value={sortKey}
							placeholder={$i18n.t('Sort')}
							items={[
								{ value: 'name', label: $i18n.t('Name') },
								{ value: 'created_at', label: $i18n.t('Created At') },
								{ value: 'updated_at', label: $i18n.t('Updated At') }
							]}
						/>

						{#if sortKey}
							<DropdownOptions
								align="start"
								bind:value={direction}
								items={[
									{ value: 'asc', label: $i18n.t('Asc') },
									{ value: null, label: $i18n.t('Desc') }
								]}
							/>
						{/if}
					</div>
				</div>
			</div>

			{#if fileItems !== null && fileItemsTotal !== null}
				<div class="flex flex-row flex-1 gap-3 px-2.5 mt-2">
					<div class="flex-1 flex">
						<div class=" flex flex-col w-full space-x-2 rounded-lg h-full">
							<div class="w-full h-full flex flex-col min-h-full">
								{#if fileItems.length > 0}
									<div class=" flex overflow-y-auto h-full w-full scrollbar-hidden text-xs">
										<Files
											files={fileItems}
											{knowledge}
											{selectedFileId}
											onClick={(fileId) => {
												selectedFileId = fileId;

												if (fileItems) {
													const file = fileItems.find((file) => file.id === selectedFileId);
													if (file) {
														fileSelectHandler(file);
													} else {
														selectedFile = null;
													}
												}
											}}
											onDelete={(fileId) => {
												selectedFileId = null;
												selectedFile = null;

												deleteFileHandler(fileId);
											}}
										/>
									</div>

									{#if fileItemsTotal > 30}
										<Pagination bind:page={currentPage} count={fileItemsTotal} perPage={30} />
									{/if}
								{:else}
									<div class="my-3 flex flex-col justify-center text-center text-gray-500 text-xs">
										<div>
											{$i18n.t('No content found')}
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>

					{#if selectedFileId !== null}
						<Drawer
							className="h-full"
							show={selectedFileId !== null}
							onClose={() => {
								selectedFileId = null;
								selectedFile = null;
							}}
						>
							<div class="flex flex-col justify-start h-full max-h-full">
								<div class=" flex flex-col w-full h-full max-h-full">
									<div class="shrink-0 flex items-center p-2">
										<div class="mr-2">
											<button
												class="w-full text-left text-sm p-1.5 rounded-lg dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-gray-850"
												aria-label={$i18n.t('Close')}
												on:click={() => {
													selectedFileId = null;
													selectedFile = null;
												}}
											>
												<ChevronLeft strokeWidth="2.5" />
											</button>
										</div>
										<div class=" flex-1 text-lg line-clamp-1">
											{selectedFile?.meta?.name}
										</div>

										{#if knowledge?.write_access}
											<div>
												<button
													class="flex self-center w-fit text-sm py-1 px-2.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
													disabled={isSaving}
													on:click={() => {
														updateFileContentHandler();
													}}
												>
													{$i18n.t('Save')}
													{#if isSaving}
														<div class="ml-2 self-center">
															<Spinner />
														</div>
													{/if}
												</button>
											</div>
										{/if}
									</div>

									{#key selectedFile.id}
										<textarea
											class="w-full h-full text-sm outline-none resize-none px-3 py-2"
											bind:value={selectedFileContent}
											disabled={!knowledge?.write_access}
											aria-label={$i18n.t('File content')}
											placeholder={$i18n.t('Add content here')}
										/>
									{/key}
								</div>
							</div>
						</Drawer>
					{/if}
				</div>
			{:else}
				<div class="my-10">
					<Spinner className="size-4" />
				</div>
			{/if}
		</div>
	{:else}
		<Spinner className="size-5" />
	{/if}
</div>
