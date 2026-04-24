<script lang="ts">
import { goto } from '$app/navigation';
import { getContext, onMount } from 'svelte';
import { toast } from 'svelte-sonner';

import { WEBUI_NAME, user } from '$lib/stores';
import {
deleteExpertById,
duplicateExpertById,
getExperts,
type Expert
} from '$lib/apis/experts';
import Spinner from '$lib/components/common/Spinner.svelte';
import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
import Tooltip from '$lib/components/common/Tooltip.svelte';
import Plus from '$lib/components/icons/Plus.svelte';
import Search from '$lib/components/icons/Search.svelte';
import PencilSquare from '$lib/components/icons/PencilSquare.svelte';
import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
import GarbageBin from '$lib/components/icons/GarbageBin.svelte';

const i18n = getContext('i18n');

let loading = true;
let experts: Expert[] = [];
let query = '';
let deleteTarget: Expert | null = null;
let showDeleteConfirm = false;

const loadExperts = async () => {
loading = true;
const res = await getExperts(localStorage.token).catch((error) => {
toast.error(`${error}`);
return [];
});
experts = res;
loading = false;
};

$: filteredExperts = experts.filter((expert) => {
if (!query.trim()) return true;
const q = query.toLowerCase();
return [
expert.name,
expert.description ?? '',
(expert.tags ?? []).join(' '),
expert.persona_role ?? ''
]
.join(' ')
.toLowerCase()
.includes(q);
});

const canManage = (expert: Expert) => $user?.role === 'admin' || expert.user_id === $user?.id;

const onDelete = async () => {
if (!deleteTarget) return;
const ok = await deleteExpertById(localStorage.token, deleteTarget.id).catch((error) => {
toast.error(`${error}`);
return false;
});

if (ok) {
toast.success($i18n.t('Expert deleted successfully'));
await loadExperts();
}
};

const onDuplicate = async (expert: Expert) => {
const copied = await duplicateExpertById(localStorage.token, expert.id).catch((error) => {
toast.error(`${error}`);
return null;
});

if (copied) {
toast.success($i18n.t('Expert duplicated successfully'));
await loadExperts();
}
};

onMount(async () => {
await loadExperts();
});
</script>

<svelte:head>
<title>{$i18n.t('Experts')} • {$WEBUI_NAME}</title>
</svelte:head>

<ConfirmDialog
bind:show={showDeleteConfirm}
title={$i18n.t('Delete expert?')}
on:confirm={onDelete}
>
<div class="text-sm text-gray-500">
{$i18n.t('This will delete')} <span class="font-medium">{deleteTarget?.name}</span>.
</div>
</ConfirmDialog>

<div class="px-1 py-4 flex flex-col gap-4">
<div class="flex items-center justify-between gap-3">
<div>
<div class="text-2xl font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Experts')}</div>
<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
{$i18n.t('Create and manage reusable expert agents.')}
</div>
</div>

<button
class="px-3 py-2 rounded-xl text-sm bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition flex items-center gap-2"
on:click={() => goto('/workspace/experts/create')}
>
<Plus className="size-4" />
{$i18n.t('New Expert')}
</button>
</div>

<div class="relative">
<div class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
<Search className="size-4" />
</div>
<input
bind:value={query}
class="w-full rounded-2xl pl-10 pr-3 py-2.5 text-sm bg-white dark:bg-gray-950 border border-gray-100 dark:border-gray-900 outline-hidden"
placeholder={$i18n.t('Search experts')}
/>
</div>

{#if loading}
<div class="flex justify-center py-12">
<Spinner className="size-5" />
</div>
{:else if filteredExperts.length === 0}
<div class="rounded-2xl border border-dashed border-gray-200 dark:border-gray-800 p-8 text-center text-sm text-gray-500">
{$i18n.t('No experts found')}
</div>
{:else}
<div class="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-4">
{#each filteredExperts as expert}
<div class="rounded-2xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 p-4 flex flex-col gap-3">
<div class="flex items-start justify-between gap-3">
<div class="min-w-0">
<div class="font-semibold text-gray-900 dark:text-gray-100 truncate">{expert.name}</div>
<div class="text-xs text-gray-500 mt-1">{expert.visibility}</div>
</div>

<div class="flex items-center gap-1 shrink-0">
<Tooltip content={$i18n.t('Duplicate')}>
<button class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900" on:click={() => onDuplicate(expert)}>
<DocumentDuplicate className="size-4" />
</button>
</Tooltip>

{#if canManage(expert)}
<Tooltip content={$i18n.t('Edit')}>
<button class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900" on:click={() => goto(`/workspace/experts/edit?id=${expert.id}`)}>
<PencilSquare className="size-4" />
</button>
</Tooltip>

<Tooltip content={$i18n.t('Delete')}>
<button
class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900"
on:click={() => {
deleteTarget = expert;
showDeleteConfirm = true;
}}
>
<GarbageBin className="size-4" />
</button>
</Tooltip>
{/if}
</div>
</div>

{#if expert.description}
<div class="text-sm text-gray-600 dark:text-gray-300 line-clamp-3">{expert.description}</div>
{/if}

<div class="text-sm text-gray-500 dark:text-gray-400">
{$i18n.t('Role')}: {expert.persona_role || '-'}
</div>

{#if expert.tags?.length}
<div class="flex flex-wrap gap-2">
{#each expert.tags as tag}
<div class="px-2 py-1 rounded-full text-xs bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-300">{tag}</div>
{/each}
</div>
{/if}
</div>
{/each}
</div>
{/if}
</div>
