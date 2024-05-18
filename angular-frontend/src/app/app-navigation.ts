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
        text: 'Show datasets',
        path: '/list-datasets'
      },
      {
        text: 'Upload images',
        path: '/datasets'
      },
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
