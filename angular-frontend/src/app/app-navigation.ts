export const navigation = [
  {
    text: 'Home',
    path: '/home',
    icon: 'home'
  },
  {
    text: 'Details',
    path: '/details',
    icon: 'folder'
  },
  {
    text: 'Datasets',
    icon: 'datausage',
    items: [
      {
        text: 'Upload images',
        path: '/datasets'
      },
      // {
      //   text: 'Details',
      //   path: '/details'
      // }
    ]
  },
  // {
  //   text: 'Examples',
  //   icon: 'folder',
  //   items: [
  //     {
  //       text: 'Profile',
  //       path: '/datasets'
  //     },
  //     {
  //       text: 'Details',
  //       path: '/details'
  //     }
  //   ]
  // }
];
