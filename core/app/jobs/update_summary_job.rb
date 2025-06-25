require 'net/http'
require 'uri'
require 'json'

LLM_URL = "http://100.115.151.29:8080/completion"

class UpdateSummaryJob < ApplicationJob
  queue_as :default

  def perform(chat_id, new_message)
    chat = Chat.find_by(id: chat_id)
    return unless chat

    old_summary = chat.summary || ""
    llm_response = call_llm(old_summary, new_message)
    if llm_response
      chat.update(summary: llm_response)
    end
  end

  private

  def call_llm(old_summary, new_message)
    # If starting from scratch, just use the new message as the summary
    if old_summary.blank?
      return new_message.strip
    end

    prompt = <<~PROMPT
      You are a helpful assistant. You will be given a chat history summary and a new message. Your task is to produce an updated summary of the conversation so far.

      Instructions:
      - Summarize the key points and important details from the conversation so far.
      - Do NOT invent or add unrelated information.
      - If the conversation is very short, simply repeat the main points as the summary.
      - Output ONLY the updated summary, nothing else.

      Examples:
      Previous summary:
      user: Hello, what is MARL?
      New message:
      assistant: MARL stands for Multi-Agent Reinforcement Learning.
      Updated summary:
      MARL stands for Multi-Agent Reinforcement Learning.
      ###
      Previous summary:
      user: What are the applications of MARL in robotics?
      New message:
      assistant: MARL is used in swarm robotics, autonomous vehicles, and more.
      Updated summary:
      MARL is used in swarm robotics, autonomous vehicles, and more.
      ###
      Previous summary:
      user: Can you explain the difference between MARL and RL?
      New message:
      assistant: MARL involves multiple agents, while RL typically involves a single agent.
      Updated summary:
      MARL involves multiple agents, while RL typically involves a single agent.
      ###
      Previous summary:
      #{old_summary}
      New message:
      #{new_message}
      Updated summary:
    PROMPT
    prompt += "\n###"

    llm_body = {
      prompt: prompt,
      temperature: 0.7,
      n_predict: 300,
      stream: false,
      stop: ["###"]
    }

    uri = URI.parse(LLM_URL)
    response = Net::HTTP.post(
      uri,
      llm_body.to_json,
      "Content-Type" => "application/json"
    )

    if response.is_a?(Net::HTTPSuccess)
      json = JSON.parse(response.body)
      summary = json["content"] || response.body
      # Post-process: remove any repeated prompt artifacts and trim whitespace
      summary = summary.gsub(/(Previous summary:|New message:|Updated summary:).*/im, "").strip
      # Fallback: if summary is empty or off-topic, concatenate old_summary and new_message
      if summary.blank? || summary.downcase.include?("python") || summary.downcase.include?("markdown")
        summary = [old_summary, new_message].reject(&:blank?).join(" ").strip
      end
      summary
    else
      nil
    end
  rescue => e
    Rails.logger.error("LLM call failed: #{e.message}")
    nil
  end
end
