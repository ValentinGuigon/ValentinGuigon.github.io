Jekyll::Hooks.register :site, :post_write do |site|
  articles_dir = File.join(site.config['destination'], 'articles')
  double_dated_pattern = /\d{4}-\d{2}-\d{2}-\d{4}-\d{2}-\d{2}-/

  Dir.glob(File.join(articles_dir, '*')).each do |file|
    if File.directory?(file) && File.basename(file).match?(double_dated_pattern)
      FileUtils.rm_rf(file)
      puts "Removed double-dated directory: #{file}"
    end
  end
end

Jekyll::Hooks.register :site, :pre_render do |site|
  site.posts.docs.delete_if do |post|
    post.data['slug'] =~ /\d{4}-\d{2}-\d{2}-\d{4}-\d{2}-\d{2}-/
  end
end