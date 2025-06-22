import { useState, useEffect } from "react";
import axios from "axios";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { scrypt } from "@noble/hashes/scrypt";
import { Input } from "./components/ui/input";
import { Button } from "./components/ui/button";
import { Shield, Key, Hash, Lock, Copy, EyeOff, Github, Loader2 } from "lucide-react";
import { SiBuymeacoffee } from "@icons-pack/react-simple-icons";

const urlSchema = z.object({
  url: z
    .string()
    .min(1, "URL is required")
    .url("Please enter a valid URL")
    .refine((url) => {
      try {
        const parsedUrl = new URL(url);
        return (
          parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:"
        );
      } catch {
        return false;
      }
    }, "URL must start with http:// or https://"),
});

type UrlFormData = z.infer<typeof urlSchema>;

// Configuration constants
const ALLOWED_CHARS = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ123456789+*-';
// Shared salt for lookup hash (protects against rainbow tables)
const LOOKUP_SALT = new Uint8Array([0x74, 0x6e, 0x79, 0x72, 0x2e, 0x6d, 0x65, 0x5f, 0x6c, 0x6f, 0x6f, 0x6b, 0x75, 0x70, 0x5f, 0x73]); // "tnyr.me_lookup_s"

// Crypto utilities
const generateRandomString = (length: number, chars: string = ALLOWED_CHARS) => {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return Array.from(array, byte => chars[byte % chars.length]).join('');
};

const generateRandomBytes = (length: number) => {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return array;
};

// Hash ID for lookup (using shared salt to protect against rainbow tables)
const hashIdForLookup = (id: string) => {
  const encoder = new TextEncoder();
  return scrypt(encoder.encode(id), LOOKUP_SALT, {
    N: 2 ** 17,      // CPU/memory cost
    r: 8,          // block size
    p: 1,          // parallelism
    dkLen: 32      // output length
  });
};

// Hash ID with random salt for encryption key
const deriveEncryptionKey = (id: string, salt: Uint8Array) => {
  const encoder = new TextEncoder();
  return scrypt(encoder.encode(id), salt, {
    N: 2 ** 17,      // CPU/memory cost
    r: 8,          // block size
    p: 1,          // parallelism
    dkLen: 32      // output length
  });
};

const encryptUrl = async (key: Uint8Array, plaintext: string) => {
  const iv = generateRandomBytes(16);
  const encoder = new TextEncoder();
  const data = encoder.encode(plaintext);
  
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    key,
    { name: 'AES-CBC' },
    false,
    ['encrypt']
  );
  
  const encrypted = await crypto.subtle.encrypt(
    { name: 'AES-CBC', iv: iv },
    cryptoKey,
    data
  );
  
  return { iv, encrypted: new Uint8Array(encrypted) };
};

const decryptUrl = async (key: Uint8Array, iv: Uint8Array, ciphertext: Uint8Array) => {
  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    key,
    { name: 'AES-CBC' },
    false,
    ['decrypt']
  );
  
  const decrypted = await crypto.subtle.decrypt(
    { name: 'AES-CBC', iv: iv },
    cryptoKey,
    ciphertext
  );
  
  const decoder = new TextDecoder();
  return decoder.decode(decrypted);
};

const arrayToHex = (array: Uint8Array) => {
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
};

const hexToArray = (hex: string) => {
  return new Uint8Array(hex.match(/.{1,2}/g)!.map(byte => parseInt(byte, 16)));
};

export default function App() {
  const [shortened, setShortened] = useState("");
  const [loading, setLoading] = useState(false);
  const [isDecrypting, setIsDecrypting] = useState(false);
  
  // Check for hash in URL on component mount for decryption
  useEffect(() => {
    const handleDecryption = async () => {
      const hash = window.location.hash.slice(1); // Remove # character
      if (hash && hash.length === 10) {
        setIsDecrypting(true);
        try {
          // Allow UI to update before starting heavy computation
          await new Promise(resolve => setTimeout(resolve, 20));
          
          // Hash ID directly for lookup (no salt)
          const lookupKey = hashIdForLookup(hash);
          const lookupHash = arrayToHex(lookupKey);
          
          // Get encrypted data from server
          const response = await axios.get(`http://tnyr.me/get-encrypted-url?lookup_hash=${lookupHash}`);
          const { ENCRYTION_SALT, IV, ENCRYPTED_URL } = response.data;
          
          // Derive decryption key using the encryption salt
          const encryptionSalt = hexToArray(ENCRYTION_SALT);
          
          // Allow UI to stay responsive during heavy computation
          await new Promise(resolve => setTimeout(resolve, 15));
          
          const decryptionKey = deriveEncryptionKey(hash, encryptionSalt);
          
          // Decrypt URL
          const iv = hexToArray(IV);
          const encryptedUrl = hexToArray(ENCRYPTED_URL);
          const decryptedUrl = await decryptUrl(decryptionKey, iv, encryptedUrl);
          
          // Redirect to decrypted URL
          window.location.href = decryptedUrl;
        } catch (error) {
          console.error('Failed to decrypt URL:', error);
          setIsDecrypting(false);
          // Could show an error message to user here
        }
      }
    };
    
    handleDecryption();
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
    clearErrors,
  } = useForm<UrlFormData>({
    resolver: zodResolver(urlSchema),
    mode: "onChange", // Validate on change for better UX
  });

  const onSubmit = async (data: UrlFormData) => {
    setLoading(true);
    clearErrors();

    try {
      // Allow UI to update before starting heavy computation
      await new Promise(resolve => setTimeout(resolve, 20));
      
      // Generate random values
      const linkId = generateRandomString(10);
      const encryptionSalt = generateRandomBytes(16);
      
      // Derive keys
      const lookupKey = hashIdForLookup(linkId); // Hash ID directly for lookup
      
      // Allow UI to stay responsive during second hash computation
      await new Promise(resolve => setTimeout(resolve, 15));
      
      const encryptionKey = deriveEncryptionKey(linkId, encryptionSalt); // Use random salt for encryption
      
      // Encrypt URL
      let url = data.url;
      if (!url.startsWith('https://') && !url.startsWith('http://') && !url.startsWith('magnet:')) {
        url = 'http://' + url;
      }
      
      const { iv, encrypted } = await encryptUrl(encryptionKey, url);
      
      // Send to server
      await axios.post("https://tnyr.me/shorten", {
        LOOKUP_HASH: arrayToHex(lookupKey),
        ENCRYTION_SALT: arrayToHex(encryptionSalt),
        IV: arrayToHex(iv),
        ENCRYPTED_URL: arrayToHex(encrypted)
      });
      
      const shortUrl = `tnyr.me/#${linkId}`;
      setShortened(shortUrl);
    } catch (error) {
      console.error('Encryption error:', error);
      setError("root", { message: "Error shortening URL. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(shortened);
  };

  // Decryption loading screen
  if (isDecrypting) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 text-slate-100 flex flex-col items-center justify-center p-4">
        <div className="text-center space-y-8">
          <div className="flex justify-center">
            <div className="relative">
              <Loader2 className="w-16 h-16 text-indigo-400 animate-spin" />
              <div className="absolute inset-0 w-16 h-16 border-4 border-indigo-400/20 rounded-full"></div>
            </div>
          </div>
          
          <div className="space-y-4">
            <h1 className="text-3xl font-bold">Decrypting URL</h1>
            <p className="text-slate-400 text-lg max-w-md">
              Computing hashes and securely retrieving your destination...
            </p>
          </div>
          
          <div className="flex items-center justify-center gap-2 text-slate-500">
            <Lock className="w-4 h-4" />
            <span className="text-sm">End-to-end encrypted</span>
          </div>
        </div>
      </div>
    );
  }

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
                Your links are end-to-end encrypted - your original URL never leaves your browser unencrypted.
              </p>
            </div>
          </div>

          <form
            onSubmit={handleSubmit(onSubmit)}
            className="flex flex-col space-y-4"
          >
            <Input
              type="text"
              {...register("url")}
              placeholder="Enter your long URL here"
              className="bg-slate-700/50 border-slate-600 text-lg h-14 rounded-xl"
            />
            {errors.url && (
              <p className="text-red-400 text-sm">{errors.url.message}</p>
            )}
            {errors.root && (
              <p className="text-red-400 text-sm">{errors.root.message}</p>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="h-12 text-lg rounded-xl bg-indigo-600 hover:bg-indigo-700 transition-colors"
            >
              {loading ? "Shortening..." : "Create Secure Link"}
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
                  <h3 className="font-medium mb-1">
                    End-to-End Encryption
                  </h3>
                  <p className="text-slate-400 text-sm">
                    Your URL is encrypted in your browser and never sent to our servers in plaintext. Using AES-256 encryption, only you and those you share the link with can see the destination.
                  </p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="mt-1">
                  <Hash className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="font-medium mb-1">Complete Anonymity</h3>
                  <p className="text-slate-400 text-sm">
                    There's no way to discover or list existing links. Each URL
                    exists only for those who possess the unique ID.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex gap-3">
                <div className="mt-1">
                  <Key className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="font-medium mb-1">Secure By Design</h3>
                  <p className="text-slate-400 text-sm">
                    We derive two separate keys from your link ID. One is used to create a lookup hash, so we can find your encrypted data. The other is used to encrypt your destination URL. Without the original link ID, the data is just random noise.
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
                    We never log IP addresses, track users, or use cookies. Each
                    request is completely anonymous - your browsing activity
                    leaves no trace in our systems.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 bg-slate-700/30 rounded-lg border border-slate-700/50">
            <p className="text-sm text-slate-400">
              🔒 <span className="font-medium">Important:</span> Make sure to
              Bookmark your tnyr.me links safely - there's no way to recover
              lost IDs or access links without them.
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
