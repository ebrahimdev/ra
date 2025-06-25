require "test_helper"

class EmbeddingsControllerTest < ActionDispatch::IntegrationTest
  test "should get create" do
    get embeddings_create_url
    assert_response :success
  end
end
