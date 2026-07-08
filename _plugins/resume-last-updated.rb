require 'open3'
require 'time'

module Jekyll
  class ResumeLastUpdatedGenerator < Generator
    priority :low

    def generate(site)
      site.pages.each do |page|
        next unless page.data['layout'] == 'resume'
        next unless page.data['cv_pdf']

        relative_path = File.join('assets', 'pdf', page.data['cv_pdf'])
        page.data['resume_last_updated_source'] = relative_path

        timestamp = last_commit_timestamp(site.source, relative_path)
        next unless timestamp

        page.data['resume_last_updated'] = timestamp
      end
    end

    private

    def last_commit_timestamp(repo_root, relative_path)
      stdout, status = Open3.capture2(
        'git', 'log', '-1', '--format=%cI', '--', relative_path,
        chdir: repo_root
      )

      return Time.iso8601(stdout.strip) if status.success? && !stdout.strip.empty?

      Jekyll.logger.warn(
        'resume-last-updated:',
        "Unable to resolve Git history for #{relative_path}"
      )
      nil
    rescue StandardError => e
      Jekyll.logger.warn(
        'resume-last-updated:',
        "Unable to parse Git history for #{relative_path} (#{e.message})"
      )
      nil
    end
  end
end
