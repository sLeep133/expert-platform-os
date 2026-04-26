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
let activeTab: 'all' | 'mine' = 'all';
let activeTag = '全部';
let selectedExpert: Expert | null = null;
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

const canManage = (expert: Expert) => $user?.role === 'admin' || expert.user_id === $user?.id;

const openChatWithExpert = async (expert: Expert) => {
	const modelQuery = expert.runtime_model ? `&model=${encodeURIComponent(expert.runtime_model)}` : '';
	await goto(`/?expert=${encodeURIComponent(expert.id)}${modelQuery}`);
};

const closeExpertDetail = () => {
	selectedExpert = null;
};

const getExpertSummary = (expert: Expert) =>
	expert.description?.trim() || expert.persona_role?.trim() || '已关联知识空间，可直接进入聊天。';

const getExpertCover = (expert: Expert) => {
	if (expert.avatar?.trim()) return expert.avatar.trim();
	return '';
};

const getExpertBadge = (expert: Expert) => {
	if (canManage(expert)) return '我的专家';
	if (expert.visibility === 'shared') return '共享专家';
	return '专家';
};

const getExpertInitial = (expert: Expert) => expert.name?.trim()?.slice(0, 1).toUpperCase() || '专';

const formatDate = (timestamp: number) => {
	if (!timestamp) return '刚刚更新';
	return new Intl.DateTimeFormat('zh-CN', {
		month: 'numeric',
		day: 'numeric'
	}).format(new Date(timestamp));
};

$: tagOptions = ['全部', ...Array.from(new Set(experts.flatMap((expert) => expert.tags ?? []))).slice(0, 10)];

$: tabItems = [
	{ id: 'all', label: '专家广场', count: experts.length },
	{ id: 'mine', label: '我的专家', count: experts.filter((expert) => canManage(expert)).length }
];

$: filteredExperts = experts.filter((expert) => {
	if (activeTab === 'mine' && !canManage(expert)) return false;
	if (activeTag !== '全部' && !(expert.tags ?? []).includes(activeTag)) return false;
	if (!query.trim()) return true;

	const q = query.toLowerCase();
	return [
		expert.name,
		expert.description ?? '',
		(expert.tags ?? []).join(' '),
		expert.persona_role ?? '',
		(expert.knowledge_spaces ?? []).join(' ')
	]
		.join(' ')
		.toLowerCase()
		.includes(q);
});

const onDelete = async () => {
	if (!deleteTarget) return;
	const ok = await deleteExpertById(localStorage.token, deleteTarget.id).catch((error) => {
		toast.error(`${error}`);
		return false;
	});

	if (ok) {
		if (selectedExpert?.id === deleteTarget.id) {
			selectedExpert = null;
		}
		toast.success('专家已删除');
		await loadExperts();
	}
};

const onDuplicate = async (expert: Expert) => {
	const copied = await duplicateExpertById(localStorage.token, expert.id).catch((error) => {
		toast.error(`${error}`);
		return null;
	});

	if (copied) {
		toast.success('专家已复制');
		await loadExperts();
	}
};

onMount(async () => {
	await loadExperts();
});
</script>

<svelte:head>
	<title>专家中心 • {$WEBUI_NAME}</title>
</svelte:head>

<ConfirmDialog bind:show={showDeleteConfirm} title="删除专家？" on:confirm={onDelete}>
	<div class="text-sm text-gray-500">
		将删除专家 <span class="font-medium">{deleteTarget?.name}</span>。
	</div>
</ConfirmDialog>

<div class="px-1 py-4 flex flex-col gap-5">
	<div class="rounded-[28px] border border-gray-100 dark:border-gray-900 bg-linear-to-br from-white to-gray-50 dark:from-gray-950 dark:to-gray-900 p-5 md:p-6">
		<div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
			<div class="max-w-2xl">
				<div class="text-3xl font-semibold text-gray-900 dark:text-gray-100">专家</div>
				<div class="mt-2 text-sm text-gray-500 dark:text-gray-400">
					把模型、知识空间和业务角色封装成可直接使用的专家入口。
				</div>
				<div class="mt-4 flex flex-wrap gap-2 text-xs">
					<div class="rounded-full bg-white dark:bg-gray-950 border border-gray-100 dark:border-gray-800 px-3 py-1.5 text-gray-600 dark:text-gray-300">
						专家总数 {experts.length}
					</div>
					<div class="rounded-full bg-white dark:bg-gray-950 border border-gray-100 dark:border-gray-800 px-3 py-1.5 text-gray-600 dark:text-gray-300">
						我的专家 {experts.filter((expert) => canManage(expert)).length}
					</div>
					<div class="rounded-full bg-white dark:bg-gray-950 border border-gray-100 dark:border-gray-800 px-3 py-1.5 text-gray-600 dark:text-gray-300">
						共享专家 {experts.filter((expert) => expert.visibility === 'shared').length}
					</div>
				</div>
			</div>

			<button
				class="px-4 py-2.5 rounded-2xl text-sm bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition flex items-center justify-center gap-2"
				on:click={() => goto('/workspace/experts/create')}
			>
				<Plus className="size-4" />
				创建专家
			</button>
		</div>
	</div>

	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
			<div class="flex items-center gap-1 overflow-x-auto scrollbar-none">
				{#each tabItems as tab}
					<button
						type="button"
						class="shrink-0 rounded-full px-4 py-2 text-sm transition {activeTab === tab.id
							? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
							: 'bg-white dark:bg-gray-950 border border-gray-100 dark:border-gray-900 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}"
						on:click={() => {
							activeTab = tab.id as 'all' | 'mine';
						}}
					>
						{tab.label}
						<span class="ml-1 text-xs opacity-70">{tab.count}</span>
					</button>
				{/each}
			</div>

			<div class="relative w-full xl:max-w-sm">
				<div class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
					<Search className="size-4" />
				</div>
				<input
					bind:value={query}
					class="w-full rounded-2xl pl-10 pr-3 py-2.5 text-sm bg-white dark:bg-gray-950 border border-gray-100 dark:border-gray-900 outline-hidden"
					placeholder="搜索专家、角色或标签"
				/>
			</div>
		</div>

		<div class="flex flex-wrap gap-2">
			{#each tagOptions as tag}
				<button
					type="button"
					class="rounded-full px-3 py-1.5 text-xs transition {activeTag === tag
						? 'bg-gray-900 text-white dark:bg-white dark:text-gray-900'
						: 'bg-white dark:bg-gray-950 border border-gray-100 dark:border-gray-900 text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}"
					on:click={() => {
						activeTag = tag;
					}}
				>
					{tag}
				</button>
			{/each}
		</div>
	</div>

	{#if loading}
		<div class="flex justify-center py-16">
			<Spinner className="size-5" />
		</div>
	{:else if filteredExperts.length === 0}
		<div class="rounded-[28px] border border-dashed border-gray-200 dark:border-gray-800 p-10 text-center text-sm text-gray-500">
			当前筛选条件下暂无专家。
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-4">
			{#each filteredExperts as expert}
				<div
					role="button"
					tabindex="0"
					class="group text-left rounded-[24px] border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 p-4 hover:border-gray-300 dark:hover:border-gray-700 hover:shadow-lg transition flex flex-col gap-4 cursor-pointer"
					on:click={() => {
						selectedExpert = expert;
					}}
					on:keydown={(e) => {
						if (e.key === 'Enter' || e.key === ' ') {
							e.preventDefault();
							selectedExpert = expert;
						}
					}}
				>
					<div class="flex items-start justify-between gap-3">
						<div class="flex items-center gap-3 min-w-0">
							{#if getExpertCover(expert)}
								<img
									src={getExpertCover(expert)}
									alt={expert.name}
									class="size-11 rounded-2xl object-cover border border-gray-100 dark:border-gray-800"
								/>
							{:else}
								<div class="size-11 rounded-2xl bg-gray-100 dark:bg-gray-900 text-gray-700 dark:text-gray-200 flex items-center justify-center text-lg font-semibold">
									{getExpertInitial(expert)}
								</div>
							{/if}

							<div class="min-w-0">
								<div class="font-semibold text-gray-900 dark:text-gray-100 truncate">{expert.name}</div>
								<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">{getExpertBadge(expert)}</div>
							</div>
						</div>

						<div class="text-xs text-gray-400 shrink-0">{formatDate(expert.updated_at)}</div>
					</div>

					<div class="text-sm text-gray-600 dark:text-gray-300 line-clamp-3 min-h-[60px]">
						{getExpertSummary(expert)}
					</div>

					<div class="grid grid-cols-3 gap-2 text-center">
						<div class="rounded-2xl bg-gray-50 dark:bg-gray-900/60 px-2 py-2">
							<div class="text-xs text-gray-400">知识空间</div>
							<div class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
								{expert.knowledge_spaces?.length ?? 0}
							</div>
						</div>
						<div class="rounded-2xl bg-gray-50 dark:bg-gray-900/60 px-2 py-2">
							<div class="text-xs text-gray-400">重点页</div>
							<div class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
								{expert.knowledge_pinned_pages?.length ?? 0}
							</div>
						</div>
						<div class="rounded-2xl bg-gray-50 dark:bg-gray-900/60 px-2 py-2">
							<div class="text-xs text-gray-400">模型</div>
							<div class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
								{expert.runtime_model || '默认'}
							</div>
						</div>
					</div>

					{#if expert.tags?.length}
						<div class="flex flex-wrap gap-2">
							{#each expert.tags.slice(0, 4) as tag}
								<div class="px-2.5 py-1 rounded-full text-xs bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-300">
									{tag}
								</div>
							{/each}
						</div>
					{/if}

					<div class="flex items-center justify-between gap-3 pt-1">
						<button
							type="button"
							class="px-3 py-2 rounded-xl text-xs font-medium bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition"
							on:click|stopPropagation={() => openChatWithExpert(expert)}
						>
							开始聊天
						</button>

						<div class="flex items-center gap-1 shrink-0">
							<Tooltip content="复制">
								<button
									type="button"
									class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900"
									on:click|stopPropagation={() => onDuplicate(expert)}
								>
									<DocumentDuplicate className="size-4" />
								</button>
							</Tooltip>

							{#if canManage(expert)}
								<Tooltip content="编辑">
									<button
										type="button"
										class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900"
										on:click|stopPropagation={() => goto(`/workspace/experts/edit?id=${expert.id}`)}
									>
										<PencilSquare className="size-4" />
									</button>
								</Tooltip>

								<Tooltip content="删除">
									<button
										type="button"
										class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900"
										on:click|stopPropagation={() => {
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
				</div>
			{/each}
		</div>
	{/if}
</div>

{#if selectedExpert}
	<div class="fixed inset-0 z-40 bg-black/45 backdrop-blur-[2px] p-4 md:p-6" on:click={closeExpertDetail}>
		<div class="w-full max-w-2xl mx-auto mt-[8vh]">
			<div
				class="rounded-[28px] border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-950 shadow-2xl p-5 md:p-6 flex flex-col gap-5"
				on:click|stopPropagation
			>
				<div class="flex items-start justify-between gap-4">
					<div class="flex items-center gap-3 min-w-0">
						{#if getExpertCover(selectedExpert)}
							<img
								src={getExpertCover(selectedExpert)}
								alt={selectedExpert.name}
								class="size-14 rounded-2xl object-cover border border-gray-100 dark:border-gray-800"
							/>
						{:else}
							<div class="size-14 rounded-2xl bg-gray-100 dark:bg-gray-900 text-gray-700 dark:text-gray-200 flex items-center justify-center text-xl font-semibold">
								{getExpertInitial(selectedExpert)}
							</div>
						{/if}

						<div class="min-w-0">
							<div class="text-xl font-semibold text-gray-900 dark:text-gray-100">
								{selectedExpert.name}
							</div>
							<div class="mt-1 text-sm text-gray-500 dark:text-gray-400">
								{getExpertBadge(selectedExpert)} · 最近更新 {formatDate(selectedExpert.updated_at)}
							</div>
						</div>
					</div>

					<button
						type="button"
						class="rounded-xl px-3 py-2 text-sm text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-900"
						on:click={closeExpertDetail}
					>
						关闭
					</button>
				</div>

				<div class="text-sm leading-6 text-gray-600 dark:text-gray-300">
					{getExpertSummary(selectedExpert)}
				</div>

				<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
					<div class="rounded-2xl bg-gray-50 dark:bg-gray-900/60 p-3">
						<div class="text-xs text-gray-400">角色</div>
						<div class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
							{selectedExpert.persona_role || '未设置'}
						</div>
					</div>
					<div class="rounded-2xl bg-gray-50 dark:bg-gray-900/60 p-3">
						<div class="text-xs text-gray-400">知识空间</div>
						<div class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
							{selectedExpert.knowledge_spaces?.length ?? 0} 个
						</div>
					</div>
					<div class="rounded-2xl bg-gray-50 dark:bg-gray-900/60 p-3">
						<div class="text-xs text-gray-400">重点页面</div>
						<div class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
							{selectedExpert.knowledge_pinned_pages?.length ?? 0} 个
						</div>
					</div>
					<div class="rounded-2xl bg-gray-50 dark:bg-gray-900/60 p-3">
						<div class="text-xs text-gray-400">默认模型</div>
						<div class="mt-1 text-sm font-medium text-gray-900 dark:text-gray-100">
							{selectedExpert.runtime_model || '默认'}
						</div>
					</div>
				</div>

				{#if selectedExpert.tags?.length}
					<div class="flex flex-wrap gap-2">
						{#each selectedExpert.tags as tag}
							<div class="px-3 py-1.5 rounded-full text-xs bg-gray-100 dark:bg-gray-900 text-gray-600 dark:text-gray-300">
								{tag}
							</div>
						{/each}
					</div>
				{/if}

				<div class="rounded-2xl border border-gray-100 dark:border-gray-900 p-4">
					<div class="text-sm font-medium text-gray-900 dark:text-gray-100">使用方式</div>
					<div class="mt-2 text-sm text-gray-500 dark:text-gray-400 leading-6">
						进入聊天后，会自动按该专家关联的知识空间、重点页面和角色设定来回答问题。
					</div>
				</div>

				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex items-center gap-2">
						<button
							type="button"
							class="px-4 py-2.5 rounded-2xl text-sm bg-gray-900 text-white dark:bg-white dark:text-gray-900 hover:opacity-90 transition"
							on:click={() => openChatWithExpert(selectedExpert)}
						>
							开始聊天
						</button>

						{#if canManage(selectedExpert)}
							<button
								type="button"
								class="px-4 py-2.5 rounded-2xl text-sm border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900 transition"
								on:click={() => goto(`/workspace/experts/edit?id=${selectedExpert.id}`)}
							>
								编辑专家
							</button>
						{/if}
					</div>

					<div class="text-xs text-gray-400">专家 ID：{selectedExpert.id}</div>
				</div>
			</div>
		</div>
	</div>
{/if}
