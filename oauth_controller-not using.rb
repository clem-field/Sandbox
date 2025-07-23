class OauthController < ApplicationController
  def show
    provider = params[:provider]
    client = oauth_client(provider)
    redirect_to client.auth_code.authorize_url(redirect_uri: callback_oauth_url(provider))
  end

  def callback
    provider = params[:provider]
    client = oauth_client(provider)

    token = client.auth_code.get_token(params[:code], redirect_uri: callback_oauth_url(provider))
    user_info = fetch_user_info(provider, token)

    session[:user_id] = find_or_create_user(user_info, provider).id

    redirect_to root_path, notice: "Logged in successfully with #{provider.titleize}!"
  rescue OAuth2::Error => e
    redirect_to root_path, alert: "OAuth failed: #{e.description}"
  end

  private

  # Methods `oauth_client`, `fetch_user_info`, and `find_or_create_user` will be detailed in the next sections.
end
