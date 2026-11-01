import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { request } from "./api";
import type { Conversation, ConversationDetail } from "./types";

const ACTIVE_KEY = "helix.active-chats.v1";
function savedChats(): Record<string, string> {
  try {
    return JSON.parse(sessionStorage.getItem(ACTIVE_KEY) || "{}");
  } catch {
    return {};
  }
}
export function friendlyChatError(value: string) {
  if (/UsageLimitExceeded/i.test(value))
    return "The live analysis reached its budget. Retry this answer to use the updated, bounded workflow.";
  if (/unsupported evidence|reviewer withheld/i.test(value))
    return "The previous draft did not pass evidence checks. Retry the answer; unsupported claims were not published.";
  if (/Timeout|dependency did not complete/i.test(value))
    return "The service did not finish this time. Your question is saved and can be retried.";
  return value;
}

export function useChat(token?: string, profileId = "") {
  const client = useQueryClient();
  const [active, setActive] = useState<Record<string, string>>(savedChats);
  const [draft, setDraft] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [limit, setLimit] = useState(200);
  const listKey = ["conversations", token, profileId];
  const conversations = useQuery({
    queryKey: listKey,
    queryFn: () =>
      request<Conversation[]>(
        `/api/profiles/${profileId}/conversations`,
        token,
      ),
    enabled: !!token && !!profileId,
    refetchOnMount: "always",
  });
  const preferred = active[profileId];
  const conversationId = conversations.data
    ? conversations.data.find((c) => c.id === preferred)?.id ||
      conversations.data[0]?.id ||
      null
    : preferred || null;
  const detailKey = ["conversation", token, conversationId, limit];
  const detail = useQuery({
    queryKey: detailKey,
    queryFn: () =>
      request<ConversationDetail>(
        `/api/conversations/${conversationId}?limit=${limit}`,
        token,
      ),
    enabled: !!token && !!conversationId,
    refetchOnMount: "always",
    refetchInterval: (query) =>
      query.state.data?.messages.some(
        (m) => m.status === "queued" || m.status === "running",
      )
        ? 750
        : false,
  });
  const messages = detail.data?.messages ?? [];
  const pending = messages.some(
    (m) => m.status === "queued" || m.status === "running",
  );
  useEffect(() => {
    client.invalidateQueries({ queryKey: ["conversations", token, profileId] });
  }, [pending, conversationId, token, profileId, client]);
  useEffect(() => {
    setDraft("");
    setError("");
    setLimit(200);
  }, [profileId]);

  function select(id: string) {
    setActive((previous) => {
      const next = { ...previous, [profileId]: id };
      sessionStorage.setItem(ACTIVE_KEY, JSON.stringify(next));
      return next;
    });
    setDraft("");
    setError("");
    setLimit(200);
  }
  async function newChat() {
    if (!token || !profileId || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const conversation = await request<Conversation>(
        `/api/profiles/${profileId}/conversations`,
        token,
        { method: "POST", body: JSON.stringify({}) },
      );
      client.setQueryData<Conversation[]>(listKey, (value) => [
        conversation,
        ...(value || []),
      ]);
      client.setQueryData<ConversationDetail>(
        ["conversation", token, conversation.id, 200],
        { conversation, messages: [], has_more: false },
      );
      select(conversation.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }
  async function ask(value: string) {
    const question = value.trim();
    if (!question || !token || !profileId || submitting || pending) return;
    setSubmitting(true);
    setError("");
    try {
      const result = await request<{ job_id: string; conversation_id: string }>(
        "/api/messages",
        token,
        {
          method: "POST",
          body: JSON.stringify({
            profile_id: profileId,
            conversation_id: conversationId,
            question,
          }),
        },
      );
      const key = ["conversation", token, result.conversation_id, limit];
      client.setQueryData<ConversationDetail>(key, (previous) => ({
        conversation: previous?.conversation || {
          id: result.conversation_id,
          profile: profileId,
          title: question.slice(0, 70),
          created: Date.now() / 1000,
          updated: Date.now() / 1000,
        },
        messages: [
          ...(previous?.messages || []),
          {
            id: result.job_id,
            question,
            answer: null,
            error: null,
            status: "queued",
            created: Date.now() / 1000,
            events: [],
          },
        ],
        has_more: previous?.has_more || false,
      }));
      select(result.conversation_id);
      await client.invalidateQueries({
        queryKey: ["conversation", token, result.conversation_id],
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
      client.invalidateQueries({ queryKey: listKey });
    }
  }
  async function retry(id: string) {
    if (!token || submitting || pending) return;
    setSubmitting(true);
    setError("");
    try {
      await request(`/api/messages/${id}/retry`, token, { method: "POST" });
      client.setQueryData<ConversationDetail>(detailKey, (previous) =>
        previous
          ? {
              ...previous,
              messages: previous.messages.map((m) =>
                m.id === id
                  ? {
                      ...m,
                      answer: null,
                      error: null,
                      status: "queued",
                      events: [],
                    }
                  : m,
              ),
            }
          : previous,
      );
      await client.invalidateQueries({
        queryKey: ["conversation", token, conversationId],
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }
  return {
    conversations: conversations.data || [],
    conversationId,
    messages,
    draft,
    setDraft,
    busy: submitting || pending,
    submitting,
    newChat,
    select,
    ask,
    retry,
    error: error || (conversations.error || detail.error)?.message || "",
    loading: detail.isLoading && !!conversationId,
    hasMore: detail.data?.has_more,
    loadEarlier: () => setLimit((n) => Math.min(1000, n + 200)),
    title: detail.data?.conversation.title,
  };
}
