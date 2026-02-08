/**
 * Centralized Icon Exports
 *
 * All Lucide icons used in the application should be imported from this file.
 * This ensures consistency and makes it easy to track which icons are used.
 *
 * @example
 * import { Plus, Edit, Trash2 } from '@/config/icons'
 */

// === ACTION ICONS ===
export {
  Plus,           // Add/Create
  Edit,           // Edit
  Edit3,          // Edit (alternative)
  Trash2,         // Delete
  Save,           // Save
  Copy,           // Copy/Duplicate
  Download,       // Download
  Upload,         // Upload
  RefreshCw,      // Refresh
  RotateCcw,      // Reset/Undo
  Search,         // Search
  Filter,         // Filter
  Settings,       // Settings/Config
  X,              // Close/Cancel
  Check,          // Confirm/Success
} from 'lucide-vue-next'

// === STATUS ICONS ===
export {
  CheckCircle,    // Success status
  CheckCircle2,   // Success status (alternative)
  XCircle,        // Error/Failed status
  AlertCircle,    // Warning/Info
  AlertTriangle,  // Warning
  Info,           // Info
  Lock,           // Locked
  Unlock,         // Unlocked
  Snowflake,      // Frozen
} from 'lucide-vue-next'

// === NAVIGATION ICONS ===
export {
  Menu,           // Menu hamburger
  ChevronDown,    // Dropdown
  ChevronRight,   // Expand
  ChevronUp,      // Collapse
  ChevronLeft,    // Back
  ArrowRight,     // Arrow right
  ArrowLeft,      // Arrow left
  ArrowUp,        // Sort asc
  ArrowDown,      // Sort desc
  ArrowUpDown,    // Sort neutral
} from 'lucide-vue-next'

// === ENTITY ICONS ===
export {
  Package,        // Part/Item
  FileText,       // Document/Quote
  DollarSign,     // Pricing/Money
  Users,          // Contacts/People
  Building2,      // Company/Partner
  Factory,        // Manufacturing
  Cog,            // Operations
  Box,            // Box/Package
  Layers,         // Layers/Stack
  Database,       // Data/Storage
  ClipboardList,  // Batch sets
  Calendar,       // Date/Time
} from 'lucide-vue-next'

// === FILE ICONS ===
export {
  FileCheck,      // File verified
  FileX,          // File missing/error
  FileUp,         // File upload
  FileEdit,       // File edit
  FilePlus,       // New file
  FolderOpen,     // Open folder
} from 'lucide-vue-next'

// === UI/LAYOUT ICONS ===
export {
  LayoutGrid,     // Grid layout
  AlignHorizontalSpaceAround, // Horizontal arrange
  AlignVerticalSpaceAround,   // Vertical arrange
  GripVertical,   // Drag handle
  Star,           // Favorite
  Link,           // Link
  Sparkles,       // AI/Magic
  Circle,         // Dot indicator
  Inbox,          // Empty state
  LogOut,         // Logout
  Rocket,         // Launch/Start
  BarChart3,      // Chart/Stats
  Camera,         // Screenshot/Image
  Send,           // Send
  Wrench,         // Tools
  Scissors,       // Cut
  Gem,            // Premium/Special
} from 'lucide-vue-next'

// === MODULE-SPECIFIC ICONS ===
// These are aliases for semantic clarity
export {
  Cog as OperationsIcon,
  Package as MaterialIcon,
  DollarSign as PricingIcon,
  FileText as DrawingIcon,
  Users as PartnersIcon,
  ClipboardList as BatchIcon,
} from 'lucide-vue-next'

// === ICON SIZE CONSTANT (re-export from design) ===
export { ICON_SIZE } from './design'
