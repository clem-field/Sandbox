def plot_histogram(file_dir, data, label):
    mu, std = norm.fit(data)
    xmin, xmax = plt.slim(min(data)-1, max(data+1))
    x = np.linspace(xmin, xmax, 100)
    p = norm.pdf(x, mu, std)
    plt.ylabel("Distribution")
    plt.xlabel("Score")
    plt.plot(x, p, 'k', linewidth=2)
    title = label
    plt.title(title)
    plt.hist(data, density=True, alpha=0.55, color='b')
    plt.savefig(file_dir + current_date + "_histogram.jpg", bbox_inches='tight', pad_inches=0.25)

plot_histogram(file_dir, df.['score'], 'Score Distribution')