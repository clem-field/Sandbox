class SessionsController < ApplicationController
  # allow_unauthenticated_access only: %i[ new create ]
  # rate_limit to: 10, within: 3.minutes, only: :create, with: -> { redirect_to new_session_url, alert: "Try again later." }

  # def new
  #   render :new
  # end

  # def create
  # end

  # def create
  #   if user = User.authenticate_by(params.permit(:email_address, :password))
  #     start_new_session_for user
  #     redirect_to after_authentication_url
  #   else
  #     redirect_to new_session_path, alert: "Try another email address or password."
  #   end
  # end

  # def create
  #   user_info = request.env['omniauth.auth']
  #   raise user_info # Your own session management should be placed here.
  # end

  # def destroy
  #   terminate_session
  #   redirect_to root_path, notice: 'Signed out!'
  # end
end
