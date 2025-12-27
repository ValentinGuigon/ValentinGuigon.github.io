
require 'httparty'
require 'feedjira'
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
      feed_url = "#{site.config['substack_url']}/feed"
      xml = HTTParty.get(feed_url).body
      return if xml.nil?
      feed = Feedjira.parse(xml)
      process_substack_entries(site, feed.entries)
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
        create_medium_document(site, entry)
      end
    end

    def process_substack_entries(site, entries)
      entries.each do |entry|
        puts "...fetching Substack post: #{entry.url}"
        create_substack_document(site, entry)
      end
    end

    def create_document(site, source_name, url, content)
      slug = content[:title].downcase.strip.gsub(' ', '-').gsub(/[^\w-]/, '')
      path = site.in_source_dir("_posts/#{content[:published].strftime('%Y-%m-%d')}-#{slug}.md")
      doc = Jekyll::Document.new(
        path, { :site => site, :collection => site.collections['posts'] }
      )
      doc.data['external_source'] = source_name
      doc.data['title'] = content[:title]
      doc.data['feed_content'] = content[:content]
      doc.data['description'] = content[:summary]
      doc.data['date'] = content[:published]
      doc.data['redirect'] = url
      doc.data['categories'] = ['notes']
      site.collections['posts'].docs << doc
    end

    def create_medium_document(site, entry)
      date_slug = entry.published.strftime('%Y-%m-%d')
      title_slug = entry.title.downcase.strip.gsub(' ', '-').gsub(/[^\w-]/, '')
      unique_slug = "#{date_slug}-#{title_slug}"
    
      # Prevent double date in the slug
      unique_slug = unique_slug.sub(/#{date_slug}-#{date_slug}-/, "#{date_slug}-")
    
      # Check if a post with this slug already exists
      existing_post = site.posts.docs.find { |post| post.data['slug'] == unique_slug }
      if existing_post
        puts "Skipping duplicate post: #{entry.title}"
        return
      end
    
      path = site.in_source_dir("_posts/#{unique_slug}.md")
      doc = Jekyll::Document.new(path, { :site => site, :collection => site.collections['posts'] })
      
      doc.data['layout'] = 'post'
      doc.data['title'] = entry.title
      doc.data['date'] = entry.published
      doc.data['external_source'] = 'medium'
      doc.data['external_url'] = entry.url
      doc.data['description'] = entry.summary
      doc.data['categories'] = ['articles']
      doc.data['tags'] = entry.categories
      doc.data['slug'] = unique_slug
      doc.data['permalink'] = "/articles/#{unique_slug}/"
    
      content = Nokogiri::HTML.fragment(entry.content)
      content.css('h3').remove
      doc.content = content.to_html
    
      site.collections['posts'].docs << doc
    end

    def create_substack_document(site, entry)
      date_slug = entry.published.strftime('%Y-%m-%d')
      title_slug = entry.title.downcase.strip.gsub(' ', '-').gsub(/[^\w-]/, '')
      unique_slug = "#{date_slug}-#{title_slug}"
    
      # Prevent double date in the slug
      unique_slug = unique_slug.sub(/#{date_slug}-#{date_slug}-/, "#{date_slug}-")
    
      # Check if a post with this slug already exists
      existing_post = site.posts.docs.find { |post| post.data['slug'] == unique_slug }
      if existing_post
        puts "Skipping duplicate post: #{entry.title}"
        return
      end
    
      path = site.in_source_dir("_posts/#{unique_slug}.md")
      doc = Jekyll::Document.new(path, { :site => site, :collection => site.collections['posts'] })
      
      doc.data['title'] = entry.title
      doc.data['date'] = entry.published
      doc.data['external_source'] = 'substack'
      doc.data['redirect'] = entry.url
      doc.data['description'] = entry.summary
      doc.data['categories'] = ['articles']
      doc.data['tags'] = entry.categories
      doc.data['slug'] = unique_slug
    
      site.collections['posts'].docs << doc
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
  end
end
