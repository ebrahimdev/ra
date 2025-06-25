class EmbeddingsController < ApplicationController
  def create
    url = ENV.fetch("EMBEDDING_API_URL", "http://localhost:8000/embed")
    response = HTTP.post(url, json: { text: [params[:text]] })

    if response.status.success?
      data = JSON.parse(response.body.to_s)
      render json: { embedding: data["embeddings"][0] }
    else
      render json: { error: "Embedding service failed" }, status: 500
    end
  end
end
