# spec/requests/embeddings_spec.rb
require 'rails_helper'
require 'webmock/rspec'

RSpec.describe "Embeddings", type: :request do
  before do
    stub_request(:post, "http://127.0.0.1:8000/embed").
      with(body: { text: "Hello world" }.to_json).
      to_return(status: 200, body: { embedding: [0.1, 0.2, 0.3] }.to_json, headers: { 'Content-Type' => 'application/json' })
  end

  it "returns an embedding" do
    post "/embeddings", params: { text: "Hello world" }
    expect(response).to have_http_status(:success)
    expect(JSON.parse(response.body)).to include("embedding")
  end
end
