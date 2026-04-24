<script lang="ts">
import { goto } from '$app/navigation';
import { getContext, onMount } from 'svelte';
import { toast } from 'svelte-sonner';

import { createExpert } from '$lib/apis/experts';
import ExpertEditor from '$lib/components/workspace/Experts/ExpertEditor.svelte';

const i18n = getContext('i18n');

let expert = null;
let clone = false;

const onSubmit = async (form) => {
const res = await createExpert(localStorage.token, form).catch((error) => {
toast.error(`${error}`);
return null;
});

if (res) {
toast.success($i18n.t('Expert created successfully'));
await goto('/workspace/experts');
}
};

onMount(() => {
if (sessionStorage.expert) {
expert = JSON.parse(sessionStorage.expert);
sessionStorage.removeItem('expert');
clone = true;
}
});
</script>

{#key expert}
<ExpertEditor {expert} {clone} {onSubmit} />
{/key}
