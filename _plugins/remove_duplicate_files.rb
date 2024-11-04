Jekyll::Hooks.register :site, :after_reset do |site|
    posts_dir = site.in_source_dir('_posts')
    double_dated_pattern = /^\d{4}-\d{2}-\d{2}-\d{4}-\d{2}-\d{2}-/
  
    Dir.glob(File.join(posts_dir, '*.md')).each do |file|
      basename = File.basename(file)
      if basename.match?(double_dated_pattern)
        File.delete(file)
        puts "Deleted double-dated file: #{file}"
      end
    end
  end