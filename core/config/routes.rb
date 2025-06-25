Rails.application.routes.draw do
  # Define your application routes per the DSL in https://guides.rubyonrails.org/routing.html

  # Reveal health status on /up that returns 200 if the app boots with no exceptions, otherwise 500.
  # Can be used by load balancers and uptime monitors to verify that the app is live.
  get "up" => "rails/health#show", as: :rails_health_check

  post "/embeddings", to: "embeddings#create"

  # Defines the root path route ("/")
  # root "posts#index"
  namespace :api do
    post :ingest, to: 'api#ingest'
    match :ask, to: 'api#ask', via: [:get, :post]
    get :test, to: 'api#test'
    resources :chats, only: [:create] do
      member do
        match 'summary', to: 'chats#show_summary', via: [:get, :post]
      end
    end
  end
end
