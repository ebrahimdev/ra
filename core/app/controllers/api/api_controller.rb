module Api
  class ApiController < ApplicationController
    require 'net/http'
    require 'uri'
    require 'json'

    RAG_URL = "http://localhost:8000"
    LLM_URL = "http://100.115.151.29:8080/completion"

    def ingest
      body = {
        url: params[:url],
        user_id: params[:user_id]
      }.compact

      res = Net::HTTP.post(
        URI("#{RAG_URL}/ingest_paper"),
        body.to_json,
        "Content-Type" => "application/json"
      )

      render json: JSON.parse(res.body)
    end

    def ask
      response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
      response.headers["Pragma"] = "no-cache"
      response.headers["Expires"] = "0"
      
      Rails.logger.debug "Processing ask request with format: #{request.format}"
      if request.format.html?
        Rails.logger.debug "Rendering HTML view"
        Rails.logger.debug "View path: #{view_paths}"
        Rails.logger.debug "Template exists?: #{template_exists?('ask')}"
        render template: 'api/ask', layout: 'application', formats: [:html], handlers: [:erb]
      else
        Rails.logger.debug "Processing API request"
        # Step 1: search top chunks
        search_body = {
          query: params[:query],
          k: params[:k] || 3,
        }.compact

        search_res = Net::HTTP.post(
          URI("#{RAG_URL}/search"),
          search_body.to_json,
          "Content-Type" => "application/json"
        )
        search_json = JSON.parse(search_res.body)

        chunks = search_json["results"].map { |result| result["text"] } || []
        metadatas = search_json["results"].map { |result| result["metadata"] } || []

        context = chunks.each_with_index.map { |c, i| "From Paper #{i + 1}:\n#{c}" }.join("\n\n")

        # Step 2: build prompt
        prompt = "### Context:\n#{context}\n\n---\n### User Question:\n#{params[:query]}\n\n### Answer:"

        # Step 3: query LLM
        llm_body = {
          prompt: prompt,
          temperature: 0.7,
          n_predict: 300,
          stream: false,
          stop: ["###"]
        }

        llm_res = Net::HTTP.post(
          URI(LLM_URL),
          llm_body.to_json,
          "Content-Type" => "application/json"
        )

        answer = JSON.parse(llm_res.body)["content"]

        render json: {
          answer: answer,
          sources: metadatas
        }
      end
    end

    def ask_page
      render 'ask', layout: 'application', formats: [:html]
    end

    def test
      Rails.logger.debug "=== Test Action Debug ==="
      Rails.logger.debug "Request format: #{request.format}"
      Rails.logger.debug "View paths: #{view_paths.map(&:to_s)}"
      Rails.logger.debug "Template exists?: #{template_exists?('api/test')}"
      Rails.logger.debug "Layout exists?: #{template_exists?('layouts/application')}"
      Rails.logger.debug "Template path: #{lookup_context.find_template('api/test').virtual_path}"
      Rails.logger.debug "Layout path: #{lookup_context.find_template('layouts/application').virtual_path}"
      Rails.logger.debug "=== End Debug ==="
      
      # Force fresh response
      response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
      response.headers['Pragma'] = 'no-cache'
      response.headers['Expires'] = '0'
      
      render 'test', layout: false
    end
  end
end
