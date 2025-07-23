class CatalogsController < ApplicationController
  before_action :set_control, only: %i[ show edit update]
  allow_unauthenticated_access only: %i[ index show
]
  def index
    if params[:column].present?
      @controls = Catalog.order("#{params[:column]} #{params[:direction]}")
    else
      @controls = Catalog.all
      @families = Catalog.all
    end
  end

  def show
  end

  def new
    @control = Catalog.new
  end

  def create
    @control = Catalog.new(control_params)
    if @control.save
      redirect_to @control
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
  end

  def update
    @control = Catalog.find(params[:id])
    if @control.update(control_params)
      redirect_to @control
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    @control.destroy
    redirect_to catalogs_path
  end

  private
    def set_control
      @control = Catalog.find(params[:id])
    end

    # Only allow a list of trusted parameters through.
    def control_params
      params.expect(control: [ :control_id, :description, :family, :title,
    :language, :supplemental_guidance, :implementation_guidance, :nist_discussion,
    :nist_reference, :related_controls, :pvt_ref, :overlay,
    :nist_control, :check, :fix ])
    end
end
