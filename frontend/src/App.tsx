import { useState } from 'react';
import axios from 'axios';
import { Input } from './components/ui/input';
import { Button } from './components/ui/button';
import { Shield, Key, Hash, Lock, Copy, EyeOff, Github } from 'lucide-react';
import { SiBuymeacoffee } from '@icons-pack/react-simple-icons';

export default function App() {
  const [url, setUrl] = useState('');
  const [shortened, setShortened] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // const isValidUrl = (string) => {
  //   try {
  //     new URL(string);
  //     return true;
  //   } catch (_) {
  //     return false;
  //   }
  // };

  const handleSubmit = async (e: any) => {
    e.preventDefault();
    // if (!isValidUrl(url)) {
    //   setError('Please enter a valid URL');
    //   return;
    // }
    
    setLoading(true);
    try {
      const response = await axios.post('/shorten', {
        url: url
      });
      const shortUrl = `tnyr.me/${response.data.id}`;
      setShortened(shortUrl);
      setError('');
    } catch (err) {
      setError('Error shortening URL. Please try again.');
    }
    setLoading(false);
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(shortened);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 text-slate-100 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-2xl space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">tnyr.me</h1>
          <p className="text-slate-400 text-lg">
            Privacy-focused URL shortener with seamless encryption
          </p>
        </div>

        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 shadow-xl">
          <div className="flex flex-col space-y-4 mb-6 text-slate-300">
            <div className="flex items-center gap-2 justify-center">
              <Lock className="w-5 h-5" />
              <p className="text-center">
                Your links are encrypted - we can't see your destination URLs or share your links!
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
            <Input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Enter your long URL here"
              className="bg-slate-700/50 border-slate-600 text-lg h-14 rounded-xl"
            />
            {error && <p className="text-red-400 text-sm">{error}</p>}
            
            <Button
              type="submit"
              disabled={loading}
              className="h-12 text-lg rounded-xl bg-indigo-600 hover:bg-indigo-700 transition-colors"
            >
              {loading ? 'Shortening...' : 'Create Secure Link'}
            </Button>
          </form>

          {shortened && (
            <div className="mt-6 p-4 bg-slate-700/30 rounded-lg flex items-center justify-between">
              <a
                href={`https://${shortened}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-400 hover:text-indigo-300 break-all"
              >
                {shortened}
              </a>
              <Button
                variant="ghost"
                size="sm"
                onClick={copyToClipboard}
                className="text-slate-400 hover:bg-slate-600/50"
              >
                <Copy className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>
      </div>
      
      <div className="w-full max-w-3xl mt-12 mb-8">
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 shadow-xl border border-slate-700/30">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <Lock className="w-6 h-6 text-indigo-400" />
            How We Protect Your Privacy
          </h2>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-4">
              <div className="flex gap-3">
                <div className="mt-1">
                  <Shield className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="font-medium mb-1">Zero-Knowledge Encryption</h3>
                  <p className="text-slate-400 text-sm">
                    Your URL is encrypted using AES-256 with a key derived from your unique link ID. 
                    Not even we can decrypt or view your original URL.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="mt-1">
                  <Key className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="font-medium mb-1">Secure Storage</h3>
                  <p className="text-slate-400 text-sm">
                    We generate two separate hashes - one for identification and another for encrypting the destination. Without the exact ID, the link is completely inaccessible.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex gap-3">
                <div className="mt-1">
                  <Hash className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="font-medium mb-1">Complete Anonymity</h3>
                  <p className="text-slate-400 text-sm">
                    There's no way to discover or list existing links. Each URL exists 
                    only for those who possess the unique ID.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="mt-1">
                  <EyeOff className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="font-medium mb-1">Security Process</h3>
                  <p className="text-slate-400 text-sm">
                    We never log IP addresses, track users, or use cookies. Each request is completely anonymous - your browsing activity leaves no trace in our systems.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 bg-slate-700/30 rounded-lg border border-slate-700/50">
            <p className="text-sm text-slate-400">
              🔒 <span className="font-medium">Important:</span> Make sure to Bookmark your tnyr.me links safely - there's no way to recover lost IDs or access links without them.
            </p>
          </div>
        </div>
      </div>

      <footer className="bottom-4 flex items-center gap-3 text-slate-400">
        <a
          href="https://github.com/Sevi-py/tnyr.me"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-slate-300 transition-colors"
        >
          <Github className="w-8 h-8" />
        </a>
        <a
          href="https://www.buymeacoffee.com/severin.hilbert"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-slate-300 transition-colors"
        >
        <SiBuymeacoffee className="w-8 h-8" />
        </a>
      </footer>
    </div>
  );
}