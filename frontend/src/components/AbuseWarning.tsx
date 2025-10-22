import { useEffect } from 'react';

interface AbuseWarningProps {
  domain?: string;
}

export default function AbuseWarning({ domain = 'tnyr.me' }: AbuseWarningProps) {
  useEffect(() => {
    // Add meta tags to prevent indexing
    const metaRobots = document.createElement('meta');
    metaRobots.name = 'robots';
    metaRobots.content = 'noindex, nofollow';
    
    const metaGooglebot = document.createElement('meta');
    metaGooglebot.name = 'googlebot';
    metaGooglebot.content = 'noindex, nofollow';
    
    document.head.appendChild(metaRobots);
    document.head.appendChild(metaGooglebot);
    
    // Cleanup on unmount
    return () => {
      document.head.removeChild(metaRobots);
      document.head.removeChild(metaGooglebot);
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 to-purple-800 text-slate-100 flex items-center justify-center p-4">
      <div className="bg-white text-slate-900 rounded-xl p-8 md:p-12 max-w-2xl shadow-2xl">
        <div className="text-center text-6xl mb-6">⚠️</div>
        <h1 className="text-3xl font-bold text-red-600 mb-6">This Link Has Been Removed</h1>
        
        <div className="bg-red-50 border-l-4 border-red-600 p-4 mb-6 rounded">
          <p className="font-semibold text-red-900">
            This shortened URL has been disabled due to abuse reports.
          </p>
        </div>
        
        <p className="mb-4 text-slate-700">
          The link you followed has been removed from our service because it was reported for one or more of the following reasons:
        </p>
        
        <ul className="list-disc list-inside mb-6 space-y-2 text-slate-700">
          <li>Phishing or scam attempt</li>
          <li>Malware distribution</li>
          <li>Fraudulent content</li>
          <li>Harassment or threats</li>
          <li>Other malicious activity</li>
        </ul>
        
        <div className="bg-blue-50 border-l-4 border-blue-600 p-4 mb-6 rounded">
          <p className="font-semibold text-blue-900 mb-3">⚠️ Important Security Reminders:</p>
          <ul className="list-disc list-inside space-y-2 text-sm text-slate-700">
            <li>Never share personal information, passwords, or financial details through untrusted links</li>
            <li>Be cautious of urgent messages claiming your account will be locked or money is owed</li>
            <li>Verify the authenticity of communications by contacting organizations directly through official channels</li>
            <li>Legitimate companies will never ask for sensitive information via email or text messages</li>
            <li>If something seems too good to be true, it probably is</li>
          </ul>
        </div>
        
        <p className="text-sm text-slate-600 text-center">
          <strong>If you have further questions, please contact us at{' '}
          <a href={`mailto:abuse@${domain}`} className="text-blue-600 hover:text-blue-700 underline">
            abuse@{domain}
          </a></strong>
        </p>
      </div>
    </div>
  );
}

