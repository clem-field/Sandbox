module CatalogsHelper
  def sort_link(column:, label:)
    direction = column ==params[:column] ? next_direction : 'asc'
    link_to(label, catalogs_path(column: column, direction: direction), data: { turbo_action: 'replace' })
  end
  
  def next_direction
    params[:direction] == 'asc' ? 'desc' : 'asc'
  end

  def sort_indicator
    tag.span(class: "sort sort-#{params[:direction]}")
  end

  def show_sort_indicator_for(column)
    sort_indicator if params[:column] == column
  end
end
