import { Resource } from '../types';

export const MOCK_RESOURCES: Resource[] = [
  // Housing
  {
    id: '1',
    name: 'OurJourney Housing Support',
    description: 'Transitional housing and support for individuals returning from incarceration',
    category: 'housing',
    phone: '(919) 555-0100',
    address: '123 Hope St, Raleigh, NC 27601',
    website: 'https://www.ourjourney2gether.com/housing',
    isOurJourney: true
  },
  {
    id: '2',
    name: 'NC Coalition for Supportive Housing',
    description: 'Provides affordable housing options and tenant support',
    category: 'housing',
    phone: '(919) 555-0200',
    website: 'https://example.com'
  },

  // Jobs
  {
    id: '3',
    name: 'OurJourney Job Board',
    description: 'Job opportunities with employers who support second chances',
    category: 'jobs',
    website: 'https://www.ourjourney2gether.com/jobs',
    isOurJourney: true
  },
  {
    id: '4',
    name: 'NC Works Career Center',
    description: 'Job search assistance, training programs, and career counseling',
    category: 'jobs',
    phone: '(919) 555-0300',
    address: '456 Work Ave, Raleigh, NC 27601'
  },

  // Legal
  {
    id: '5',
    name: 'Legal Aid of North Carolina',
    description: 'Free legal assistance for low-income individuals',
    category: 'legal',
    phone: '1-866-219-5262',
    website: 'https://www.legalaidnc.org'
  },

  // Health
  {
    id: '6',
    name: 'Alliance Health',
    description: 'Mental health and substance use services',
    category: 'health',
    phone: '1-800-510-9132',
    website: 'https://www.alliancehealthplan.org'
  },

  // Transportation
  {
    id: '7',
    name: 'GoTriangle',
    description: 'Public transportation services in the Triangle area',
    category: 'transportation',
    phone: '(919) 485-7433',
    website: 'https://www.gotriangle.org'
  },

  // Benefits
  {
    id: '8',
    name: 'NC DHHS Benefits Portal',
    description: 'Apply for food assistance, Medicaid, and other benefits',
    category: 'benefits',
    phone: '1-800-662-7030',
    website: 'https://www.ncdhhs.gov'
  },

  // ID Documents
  {
    id: '9',
    name: 'NC DMV',
    description: 'Get your NC ID or driver\'s license',
    category: 'id-documents',
    phone: '(919) 715-7000',
    website: 'https://www.ncdot.gov/dmv'
  }
];

export const RESOURCE_CATEGORIES = [
  { id: 'id-documents', name: 'ID & Documents', nameEs: 'Identificación y Documentos', icon: 'CreditCard' },
  { id: 'housing', name: 'Housing', nameEs: 'Vivienda', icon: 'Home' },
  { id: 'jobs', name: 'Jobs & Training', nameEs: 'Empleo y Capacitación', icon: 'Briefcase' },
  { id: 'legal', name: 'Legal Help', nameEs: 'Ayuda Legal', icon: 'Scale' },
  { id: 'health', name: 'Health & Mental Health', nameEs: 'Salud y Salud Mental', icon: 'Heart' },
  { id: 'transportation', name: 'Transportation', nameEs: 'Transporte', icon: 'Bus' },
  { id: 'benefits', name: 'Benefits & Money', nameEs: 'Beneficios y Dinero', icon: 'DollarSign' },
  { id: 'education', name: 'Education', nameEs: 'Educación', icon: 'GraduationCap' },
  { id: 'family', name: 'Family Support', nameEs: 'Apoyo Familiar', icon: 'Users' },
  { id: 'probation', name: 'Probation & Parole', nameEs: 'Libertad Condicional', icon: 'ClipboardList' },
  { id: 'technology', name: 'Technology Help', nameEs: 'Ayuda Tecnológica', icon: 'Smartphone' },
  { id: 'crisis', name: 'Crisis & Emergency', nameEs: 'Crisis y Emergencia', icon: 'AlertCircle' }
];
