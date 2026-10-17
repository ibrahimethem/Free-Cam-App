# Run explicitly to prepare NoSub Studio Developer ID provisioning. No private
# key is generated/exported here. Credentials are loaded from ignored local env.
require 'dotenv'
require 'spaceship'
require 'openssl'
require 'base64'
require 'fileutils'

root = File.expand_path('..', __dir__)
Dotenv.load(File.join(__dir__, '.env'))
Dotenv.load(File.expand_path(ENV['ASC_ENV_FILE'])) unless ENV['ASC_ENV_FILE'].to_s.empty?
Spaceship::ConnectAPI.token = Spaceship::ConnectAPI::Token.create(
  key_id: ENV.fetch('ASC_KEY_ID'), issuer_id: ENV.fetch('ASC_ISSUER_ID'),
  filepath: File.expand_path(ENV.fetch('ASC_KEY_FILE'))
)
fingerprint = ENV.fetch('NOSUB_CODESIGN_IDENTITY').upcase
certificate = Spaceship::ConnectAPI::Certificate.all(filter: { certificateType: 'DEVELOPER_ID_APPLICATION' }).find do |candidate|
  der = Base64.decode64(candidate.certificate_content)
  OpenSSL::Digest::SHA1.hexdigest(der).upcase == fingerprint
end
abort 'No matching Developer ID certificate in the Apple team' unless certificate

bundles = {}
{
  'com.ethem.nosubcam.desktop' => 'NoSub Studio',
  'com.ethem.nosubcam.desktop.camera' => 'NoSub Camera Extension'
}.each do |identifier, name|
  bundles[identifier] = Spaceship::ConnectAPI::BundleId.all(filter: { identifier: identifier }).first ||
    Spaceship::ConnectAPI::BundleId.create(name: name, platform: 'MAC_OS', identifier: identifier)
end
host = bundles.fetch('com.ethem.nosubcam.desktop')
unless host.get_capabilities.any? { |capability| capability.capability_type == 'SYSTEM_EXTENSION_INSTALL' }
  host.create_capability('SYSTEM_EXTENSION_INSTALL')
end

name = "NoSub Studio Developer ID #{certificate.id}"
profile = Spaceship::ConnectAPI::Profile.all(filter: { name: name, profileType: 'MAC_APP_DIRECT' }).find(&:valid?) ||
  Spaceship::ConnectAPI::Profile.create(name: name, profile_type: 'MAC_APP_DIRECT',
    bundle_id_id: host.id, certificate_ids: [certificate.id])
output = File.join(root, 'build', 'native-camera', 'NoSubStudio.provisionprofile')
FileUtils.mkdir_p(File.dirname(output))
File.open(output, File::WRONLY | File::CREAT | File::TRUNC, 0o600) do |file|
  file.write(Base64.decode64(profile.profile_content))
end
puts "Developer ID profile prepared in ignored build/native-camera (#{profile.profile_state})."
