import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { LoginFormComponent, ResetPasswordFormComponent, CreateAccountFormComponent, ChangePasswordFormComponent } from './shared/components';
import { AuthGuardService } from './shared/services';
import { HomeComponent } from './pages/home/home.component';
import { ProfileComponent } from './pages/profile/profile.component';
import { DetailsComponent } from './pages/details/details.component';
import { DxDataGridModule, DxFormModule } from 'devextreme-angular';
import { CommonModule } from '@angular/common';
import { DatasetsComponent } from './pages/datasets/datasets.component';
import { ListDatasetsComponent } from './pages/list-datasets/list-datasets.component';
import { PatchingComponent } from './pages/patching/patching.component';
import { UnsavedChangesGuard } from './unsaved-changes';
import { RegisterRecipeComponent } from './pages/register-recipe/register-recipe.component';
import { ModelsComponent } from './pages/models/models.component';
import { ReactiveFormsModule } from '@angular/forms';

const routes: Routes = [
  {
    path: 'models',
    component: ModelsComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'register-recipe',
    component: RegisterRecipeComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'patching/:datasetName',
    component: PatchingComponent,
    canActivate: [ AuthGuardService ],
    canDeactivate: [UnsavedChangesGuard]
  },
  {
    path: 'list-datasets',
    component: ListDatasetsComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'datasets',
    component: DatasetsComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'details',
    component: DetailsComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'profile',
    component: ProfileComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'home',
    component: HomeComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'login-form',
    component: LoginFormComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'reset-password',
    component: ResetPasswordFormComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'create-account',
    component: CreateAccountFormComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: 'change-password/:recoveryCode',
    component: ChangePasswordFormComponent,
    canActivate: [ AuthGuardService ]
  },
  {
    path: '**',
    redirectTo: 'home'
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes, { useHash: true }),
            DxDataGridModule,
            DxFormModule,
            CommonModule,
            ReactiveFormsModule

          ],
  providers: [AuthGuardService],
  exports: [RouterModule],
  declarations: [
    HomeComponent,
    ProfileComponent,
    DetailsComponent
  ]
})
export class AppRoutingModule { }
