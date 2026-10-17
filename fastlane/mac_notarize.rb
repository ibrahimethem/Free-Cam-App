# Submit only the prepared NoSub desktop archive. Never save/copy the API key.
require 'dotenv'
require 'json'
require 'open3'

Dotenv.load(File.join(__dir__, '.env'))
Dotenv.load(File.expand_path(ENV['ASC_ENV_FILE'])) unless ENV['ASC_ENV_FILE'].to_s.empty?
root = File.expand_path('..', __dir__)
archive = File.join(root, 'build/native-camera/NoSub-Studio-notarization.zip')
target = File.join(root, 'dist/FreeCam.app')
if ARGV.length == 2 && ARGV.first == '--dmg'
  candidate = File.realpath(ARGV.last)
  allowed = File.join(root, 'dist/installers') + File::SEPARATOR
  abort 'Only a generated DMG inside dist/installers is allowed' unless candidate.start_with?(allowed) && candidate.end_with?('.dmg')
  archive = candidate
  target = candidate
elsif !ARGV.empty?
  abort 'Usage: mac_notarize.rb [--dmg dist/installers/package.dmg]'
end
abort 'Build and sign the native-camera app first' unless File.file?(archive)
output, errors, status = Open3.capture3('xcrun', 'notarytool', 'submit', archive,
  '--key', File.expand_path(ENV.fetch('ASC_KEY_FILE')), '--key-id', ENV.fetch('ASC_KEY_ID'),
  '--issuer', ENV.fetch('ASC_ISSUER_ID'), '--wait', '--output-format', 'json')
abort 'Notarization request failed. Check local credentials/network; no credentials were logged.' unless status.success?
result = JSON.parse(output)
File.write(File.join(root, 'build/native-camera/notarization.json'), JSON.pretty_generate(result))
puts "Notarization status: #{result['status']} (#{result['id']})"
abort 'Notarization was not accepted; do not distribute.' unless result['status'] == 'Accepted'
system('xcrun', 'stapler', 'staple', target, exception: true)
system('xcrun', 'stapler', 'validate', target, exception: true)
if target.end_with?('.dmg')
  require 'digest'
  File.write(target + '.sha256', "#{Digest::SHA256.file(target).hexdigest}  #{File.basename(target)}\n")
end
