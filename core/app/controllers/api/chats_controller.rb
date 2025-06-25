module Api
  class ChatsController < ApiController
    def show_summary
      chat = Chat.find(params[:id])
      new_message = params[:new_message] || (request.body.size > 0 ? JSON.parse(request.body.read)["new_message"] : nil)
      render json: { summary: chat.summary }
      if new_message.present?
        UpdateSummaryJob.perform_later(chat.id, new_message)
      end
    end

    def create
      summary = params[:summary] || (request.body.size > 0 ? JSON.parse(request.body.read)["summary"] : nil) || ""
      chat = Chat.create!(summary: summary)
      render json: { id: chat.id, summary: chat.summary }, status: :created
    end
  end
end 