require 'httparty'
require 'feedjira'
require 'feedjira/parser/rss'
require 'nokogiri'
require 'set'

module ExternalPosts
  class ExternalPostsGenerator < Jekyll::Generator
    safe true
    priority :high

    def generate(site)
      @existing_slugs = Set.new

      if site.config['external_sources']
        site.config['external_sources'].each do |src|
          puts "Fetching external posts from #{src['name']}:"
          if src['rss_url']
            fetch_from_rss(site, src)
          elsif src['posts']
            fetch_from_urls(site, src)
          end
        end
      end

      if site.config['medium_username']
        puts "Fetching Medium posts for #{site.config['medium_username']}:"
        fetch_medium_posts(site)
      end

      if site.config['substack_url']
        puts "Fetching Substack posts from #{site.config['substack_url']}:"
        fetch_substack_posts(site)
      end
    end

    def fetch_from_rss(site, src)
      xml = HTTParty.get(src['rss_url']).body
      return if xml.nil?
      feed = Feedjira.parse(xml)
      process_entries(site, src, feed.entries)
    end

    def fetch_medium_posts(site)
      feed_url = "https://medium.com/feed/@#{site.config['medium_username']}"
      xml = HTTParty.get(feed_url).body
      return if xml.nil?
      feed = Feedjira.parse(xml)
      process_medium_entries(site, feed.entries)
    end

    def fetch_substack_posts(site)
      cached_path = site.in_source_dir('_data/substack_feed.xml')
      if File.exist?(cached_path)
        puts "Using cached Substack feed: _data/substack_feed.xml"
        begin
          feed = Feedjira.parse(File.read(cached_path))
          puts "...parsed cached feed entries=#{feed&.entries&.length || 0}"
          return process_substack_entries(site, feed.entries || [])
        rescue => e
          puts "...failed to parse cached Substack feed: #{e}"
        end
      else
        puts "Cached Substack feed not found at _data/substack_feed.xml"
      end
    end

    def process_entries(site, src, entries)
      entries.each do |e|
        puts "...fetching #{e.url}"
        create_document(site, src['name'], e.url, {
          title: e.title,
          content: e.content,
          summary: e.summary,
          published: e.published
        })
      end
    end

    def process_medium_entries(site, entries)
      entries.each do |entry|
        puts "...fetching Medium post: #{entry.url}"
        debug_entry(entry, 'medium')
        create_external_document(site, entry, 'medium', "/articles/#{generate_unique_slug(entry)}/")
      end
    end

    def process_substack_entries(site, entries)
      entries.each do |entry|
        puts "...fetching Substack post: #{entry.url}"
        debug_entry(entry, 'substack')
        create_external_document(site, entry, 'substack')
      end
    end

    def create_document(site, source_name, url, content)
      slug = generate_slug_from_title_and_date(content[:title], content[:published])
      doc = build_and_populate_doc(site, slug, {
        title: content[:title],
        date: content[:published],
        external_source: source_name,
        description: content[:summary],
        categories: ['notes']
      })
      doc.data['feed_content'] = content[:content]
      doc.data['redirect'] = url
      site.collections['posts'].docs << doc
    end

    def create_external_document(site, entry, source, permalink = nil)
      unique_slug = generate_unique_slug(entry)
      doc = build_and_populate_doc(site, unique_slug, {
        title: entry.title,
        date: entry.published,
        external_source: source,
        description: entry.summary,
        categories: ['articles'],
        tags: entry.categories
      })
      doc.data['layout'] = 'post'
      doc.data['external_url'] = entry.url
      doc.data['slug'] = unique_slug
      doc.data['permalink'] = permalink if permalink
      doc.data['feed_content'] = entry.content if entry.respond_to?(:content) && entry.content

      if source == 'medium'
        content = Nokogiri::HTML.fragment(entry.content)
        content.css('h3').remove
        doc.content = content.to_html
      end

      site.collections['posts'].docs << doc
    end

    # Helper: build a Jekyll document and populate shared fields
    def build_and_populate_doc(site, slug, attrs = {})
      doc = create_jekyll_document(site, build_post_path(site, slug))
      doc.data['title'] = attrs[:title] if attrs[:title]
      doc.data['date'] = attrs[:date] if attrs[:date]
      doc.data['external_source'] = attrs[:external_source] if attrs[:external_source]
      doc.data['description'] = attrs[:description] if attrs[:description]
      doc.data['categories'] = attrs[:categories] if attrs[:categories]
      doc.data['tags'] = attrs[:tags] if attrs[:tags]
      doc
    end

    def build_post_path(site, slug)
      site.in_source_dir("_posts/#{slug}.md")
    end

    def create_jekyll_document(site, path)
      Jekyll::Document.new(path, site: site, collection: site.collections['posts'])
    end

    def generate_unique_slug(entry)
      generate_slug_from_title_and_date(entry.title, entry.published)
    end

    def generate_slug_from_title_and_date(title, published_date)
      # Allow missing published_date (fallback to today UTC)
      pd = published_date || Time.now.utc
      date_slug = pd.strftime('%Y-%m-%d')
      title_slug = (title || '').to_s.downcase.strip.gsub(' ', '-').gsub(/[^\w-]/, '')
      "#{date_slug}-#{title_slug}"
    end


    def fetch_from_urls(site, src)
      src['posts'].each do |post|
        puts "...fetching #{post['url']}"
        content = fetch_content_from_url(post['url'])
        content[:published] = parse_published_date(post['published_date'])
        create_document(site, src['name'], post['url'], content)
      end
    end

    def parse_published_date(published_date)
      case published_date
      when String
        Time.parse(published_date).utc
      when Date
        published_date.to_time.utc
      else
        raise "Invalid date format for #{published_date}"
      end
    end

    def fetch_content_from_url(url)
      html = HTTParty.get(url).body
      parsed_html = Nokogiri::HTML(html)

      title = parsed_html.at('head title')&.text || ''
      description = parsed_html.at('head meta[name="description"]')&.attr('content') || ''
      body_content = parsed_html.at('body')&.inner_html || ''

      {
        title: title,
        content: body_content,
        summary: description
      }
    end

    # Debug helper: print concise info about a feed entry
    def debug_entry(entry, source)
      puts "DEBUG ENTRY (#{source.upcase}): class=#{entry.class}"
      puts "  title: #{entry.title.inspect}"
      puts "  url: #{entry.url.inspect}"
      puts "  published: #{entry.respond_to?(:published) ? entry.published.inspect : 'N/A'}"
      puts "  has_content?: #{entry.respond_to?(:content) && !entry.content.to_s.strip.empty?}"
      puts "  content_len: #{entry.respond_to?(:content) ? entry.content.to_s.length : 'N/A'}"
      puts "  summary: #{entry.respond_to?(:summary) ? entry.summary.inspect : 'N/A'}"
      puts "  categories: #{entry.respond_to?(:categories) ? entry.categories.inspect : 'N/A'}"
      puts "  raw_trunc: #{entry.to_s[0,500].gsub(/\n/, ' ')}"
    end
  end
end
