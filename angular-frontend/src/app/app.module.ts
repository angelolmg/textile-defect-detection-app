import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { AppComponent } from './app.component';
import { SideNavOuterToolbarModule, SideNavInnerToolbarModule, SingleCardModule } from './layouts';
import { FooterModule, ResetPasswordFormModule, CreateAccountFormModule, ChangePasswordFormModule, LoginFormModule } from './shared/components';
import { AuthService, ScreenService, AppInfoService } from './shared/services';
import { UnauthenticatedContentModule } from './unauthenticated-content';
import { AppRoutingModule } from './app-routing.module';
import {HttpClientModule} from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { DatasetsComponent } from './pages/datasets/datasets.component';
import { FormsModule } from '@angular/forms';
import { ListDatasetsComponent } from './pages/list-datasets/list-datasets.component';
import { RouterModule } from '@angular/router';
import { PatchingComponent } from './pages/patching/patching.component';

@NgModule({
  declarations: [
    AppComponent,
    DatasetsComponent,
    ListDatasetsComponent,
    PatchingComponent
  ],
  imports: [
    CommonModule,
    BrowserModule,
    SideNavOuterToolbarModule,
    SideNavInnerToolbarModule,
    SingleCardModule,
    FooterModule,
    ResetPasswordFormModule,
    CreateAccountFormModule,
    ChangePasswordFormModule,
    LoginFormModule,
    UnauthenticatedContentModule,
    AppRoutingModule,
    HttpClientModule,
    FormsModule,
    RouterModule


  ],
  providers: [
    AuthService,
    ScreenService,
    AppInfoService
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
