from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks
from ..models.chat_summary import ChatSummary
from ..utils.llm_client import call_llm

class ChatSummaryService:
    @staticmethod
    async def create_summary(session: AsyncSession, summary: str = "") -> ChatSummary:
        chat = ChatSummary(summary=summary)
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
        return chat

    @staticmethod
    async def get_summary(session: AsyncSession, chat_id: int) -> ChatSummary:
        result = await session.execute(select(ChatSummary).where(ChatSummary.id == chat_id))
        chat = result.scalar_one_or_none()
        if not chat:
            raise NoResultFound(f"ChatSummary with id {chat_id} not found")
        return chat

    @staticmethod
    async def update_summary(session: AsyncSession, chat_id: int, new_message: str, background_tasks: BackgroundTasks = None) -> ChatSummary:
        chat = await ChatSummaryService.get_summary(session, chat_id)
        old_summary = chat.summary or ""
        if background_tasks:
            background_tasks.add_task(ChatSummaryService._update_summary_llm, chat_id, old_summary, new_message)
            return chat
        else:
            await ChatSummaryService._update_summary_llm(session, chat, old_summary, new_message)
            return chat

    @staticmethod
    async def _update_summary_llm(session: AsyncSession = None, chat: ChatSummary = None, old_summary: str = "", new_message: str = "", chat_id: int = None):
        # If called from background task, get a new session and chat object
        if session is None and chat_id is not None:
            from ..services.db import get_db
            async for db_session in get_db():
                session = db_session
                break
            
            # Get fresh chat object
            chat = await ChatSummaryService.get_summary(session, chat_id)
        
        prompt = f"""You are a helpful assistant. You will be given a chat history summary and a new message. Your task is to produce an updated summary of the conversation so far.\n\nInstructions:\n- Summarize the key points and important details from the conversation so far.\n- Do NOT invent or add unrelated information.\n- If the conversation is very short, simply repeat the main points as the summary.\n- Output ONLY the updated summary, nothing else.\n\nPrevious summary:\n{old_summary}\nNew message:\n{new_message}\nUpdated summary:"""
        prompt += "\n###"
        
        try:
            llm_response = call_llm(prompt)
            if chat and hasattr(chat, 'summary'):
                chat.summary = llm_response.strip() if llm_response else f"{old_summary} {new_message}".strip()
                await session.commit()
                await session.refresh(chat)
        except Exception as e:
            # If LLM fails, just concatenate the messages
            if chat and hasattr(chat, 'summary'):
                chat.summary = f"{old_summary} {new_message}".strip()
                await session.commit()
                await session.refresh(chat) 