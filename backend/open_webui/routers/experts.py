import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.models.experts import (
    ExpertForm,
    ExpertModel,
    ExpertResponse,
    ExpertUserModel,
    Experts,
)
from open_webui.models.users import UserModel
from open_webui.utils.auth import get_verified_user

log = logging.getLogger(__name__)

router = APIRouter()


############################
# GetExperts
############################


@router.get('/', response_model=list[ExpertUserModel])
async def get_experts(user=Depends(get_verified_user)):
    if user.role == 'admin':
        return await Experts.get_experts()
    return await Experts.get_experts_by_user_id(user.id)


############################
# CreateNewExpert
############################


@router.post('/create', response_model=Optional[ExpertResponse])
async def create_new_expert(
    form_data: ExpertForm,
    user=Depends(get_verified_user),
):
    expert = await Experts.insert_new_expert(user.id, form_data)
    if expert:
        return expert
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail='Failed to create expert.',
    )


############################
# GetExpertById
############################


@router.get('/{id}', response_model=Optional[ExpertResponse])
async def get_expert_by_id(id: str, user=Depends(get_verified_user)):
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and expert.visibility != 'shared' and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )
    return expert


############################
# UpdateExpertById
############################


@router.post('/{id}/update', response_model=Optional[ExpertResponse])
async def update_expert_by_id(
    id: str,
    form_data: ExpertForm,
    user=Depends(get_verified_user),
):
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )
    updated = await Experts.update_expert_by_id(id, form_data)
    if updated:
        return updated
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail='Failed to update expert.',
    )


############################
# DeleteExpertById
############################


@router.delete('/{id}/delete', response_model=bool)
async def delete_expert_by_id(id: str, user=Depends(get_verified_user)):
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )
    if expert.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access prohibited.',
        )
    return await Experts.delete_expert_by_id(id)


############################
# DuplicateExpert
############################


@router.post('/{id}/duplicate', response_model=Optional[ExpertResponse])
async def duplicate_expert_by_id(id: str, user=Depends(get_verified_user)):
    expert = await Experts.get_expert_by_id(id)
    if not expert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Expert not found.',
        )

    from open_webui.models.experts import (
        PersonaForm,
        MethodForm,
        RuntimeForm,
        KnowledgeViewForm,
    )

    form_data = ExpertForm(
        name=f'{expert.name} (Copy)',
        description=expert.description,
        avatar=expert.avatar,
        tags=expert.tags,
        visibility='private',
        persona=PersonaForm(
            role=expert.persona_role,
            tone=expert.persona_tone,
            style=expert.persona_style,
            constraints=expert.persona_constraints,
        ),
        method=MethodForm(
            principles=expert.method_principles,
            workflows=expert.method_workflows,
            output_preferences=expert.method_output_preferences,
        ),
        runtime=RuntimeForm(
            model=expert.runtime_model,
            provider=expert.runtime_provider,
            context_budget=expert.runtime_context_budget,
            tool_policy=expert.runtime_tool_policy,
            collaboration_mode=expert.runtime_collaboration_mode,
        ),
        knowledge_view=KnowledgeViewForm(
            spaces=expert.knowledge_spaces,
            pinned_pages=expert.knowledge_pinned_pages,
            source_filters=expert.knowledge_source_filters,
        ),
        system_prompt=expert.system_prompt,
    )

    new_expert = await Experts.insert_new_expert(user.id, form_data)
    if new_expert:
        return new_expert
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail='Failed to duplicate expert.',
    )

