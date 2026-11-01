import { MessageSquare } from "lucide-react";
import type { Conversation } from "../types";

export function ChatList({
  chats,
  activeId,
  onSelect,
}: {
  chats: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="chat-list" aria-label="Saved conversations">
      {chats.length ? (
        chats.map((chat) => (
          <button
            key={chat.id}
            className={`chat-list-item ${activeId === chat.id ? "selected" : ""}`}
            aria-label={`Open chat: ${chat.title}`}
            aria-current={activeId === chat.id ? "page" : undefined}
            title={chat.title}
            onClick={() => onSelect(chat.id)}
          >
            <MessageSquare size={14} />
            <span>{chat.title}</span>
          </button>
        ))
      ) : (
        <p className="chat-list-empty">
          Start a conversation. Your chats will be saved here.
        </p>
      )}
    </div>
  );
}
